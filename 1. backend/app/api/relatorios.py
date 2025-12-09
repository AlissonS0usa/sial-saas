# app/api/relatorios.py

from datetime import datetime, timedelta
from typing import Optional, List

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from app.models.dispositivo import Dispositivo
from app.models.leitura import Leitura
from app.models.usuario import Usuario  
from app.core.deps import get_usuario_logado, get_db  
from app.schemas.leitura import (
    RelatorioDispositivoOut,
    RelatorioDispositivoMetricas,
    SeriesRelatorioDispositivo,
    PontoUmidade,
)

import hashlib

# Monkey patch para o md5 do ReportLab funcionar no Anaconda/Windows
_original_md5 = hashlib.md5

def md5_compat(*args, **kwargs):
    # ignora o argumento "usedforsecurity", se for passado
    kwargs.pop("usedforsecurity", None)
    return _original_md5(*args, **kwargs)

hashlib.md5 = md5_compat

from io import BytesIO, StringIO
import csv

# se você não tiver o reportlab instalado, vai precisar instalar no ambiente:
# pip install reportlab
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas

router = APIRouter()


def _is_admin(user: Usuario) -> bool:
    role = getattr(user, "role", None)
    if role is None:
        return False
    if isinstance(role, str):
        return role.upper() == "ADMIN"
    return getattr(role, "name", str(role)).upper() == "ADMIN"


def _montar_relatorio_dispositivo(
    db: Session,
    dispositivo_id: str,
    inicio: Optional[datetime],
    fim: Optional[datetime],
    current_user: Usuario,
) -> RelatorioDispositivoOut:
    """Função de serviço que monta o relatório (usada pelo JSON, PDF e CSV)."""

    # 1) Busca o dispositivo
    dispositivo: Dispositivo | None = (
        db.query(Dispositivo).filter(Dispositivo.id == dispositivo_id).first()
    )
    if not dispositivo:
        raise HTTPException(status_code=404, detail="Dispositivo não encontrado.")

    # 2) Verifica permissão básica
    if not _is_admin(current_user):
        owner_id = getattr(dispositivo, "usuario_id", None)
        if owner_id is not None and owner_id != current_user.id:
            raise HTTPException(status_code=403, detail="Sem permissão para esse dispositivo.")

    # 3) Período padrão: últimas 24h
    if fim is None:
        fim = datetime.utcnow()
    if inicio is None:
        inicio = fim - timedelta(days=1)

    if inicio >= fim:
        raise HTTPException(status_code=400, detail="Período inválido.")

    # 4) Busca leituras
    leituras: List[Leitura] = (
        db.query(Leitura)
        .filter(
            Leitura.dispositivo_id == dispositivo.id,
            Leitura.timestamp >= inicio,
            Leitura.timestamp <= fim,
        )
        .order_by(Leitura.timestamp.asc())
        .all()
    )

    total_leituras = len(leituras)

    # 5) Faixa alvo
    cfg = dispositivo.config or {}
    parametros = cfg.get("parametros") or {}
    umid_min_alvo = parametros.get("umidadeMinima")
    umid_max_alvo = parametros.get("umidadeMaxima")

    # 6) Série de umidade + métricas simples
    umidades: list[float] = []
    pontos_umidade: list[PontoUmidade] = []
    dentro_faixa = 0
    fora_faixa = 0

    for leitura in leituras:
        dados = leitura.dados or {}
        if "umidade" in dados:
            try:
                u = float(dados["umidade"])
            except (ValueError, TypeError):
                continue

            umidades.append(u)
            pontos_umidade.append(
                PontoUmidade(timestamp=leitura.timestamp, umidade=u)
            )

            if umid_min_alvo is not None and umid_max_alvo is not None:
                if umid_min_alvo <= u <= umid_max_alvo:
                    dentro_faixa += 1
                else:
                    fora_faixa += 1

    leituras_com_umidade = len(umidades)

    if leituras_com_umidade > 0:
        umidade_min = min(umidades)
        umidade_max = max(umidades)
        umidade_media = sum(umidades) / leituras_com_umidade
    else:
        umidade_min = umidade_max = umidade_media = None

    percentual_dentro_faixa: Optional[float] = None
    if leituras_com_umidade > 0 and (dentro_faixa + fora_faixa) > 0:
        percentual_dentro_faixa = (dentro_faixa / (dentro_faixa + fora_faixa)) * 100.0

    metricas = RelatorioDispositivoMetricas(
        umidade_min=umidade_min,
        umidade_max=umidade_max,
        umidade_media=umidade_media,
        leituras_total=total_leituras,
        leituras_com_umidade=leituras_com_umidade,
        dentro_faixa=dentro_faixa if leituras_com_umidade > 0 else None,
        fora_faixa=fora_faixa if leituras_com_umidade > 0 else None,
        percentual_dentro_faixa=percentual_dentro_faixa,
    )

    series = SeriesRelatorioDispositivo(umidade=pontos_umidade)

    dispositivo_info = {
        "id": str(dispositivo.id),
        "nome": getattr(dispositivo, "nome", None),
        "tipo": getattr(dispositivo, "tipo", None),
        "cliente_nome": getattr(getattr(dispositivo, "usuario", None), "nome", None),
        "lugar_nome": getattr(getattr(dispositivo, "lugar", None), "nome", None),
    }

    periodo_info = {
        "inicio": inicio,
        "fim": fim,
    }

    parametros_alvo = {
        "umidadeMinima": umid_min_alvo,
        "umidadeMaxima": umid_max_alvo,
    }

    return RelatorioDispositivoOut(
        dispositivo=dispositivo_info,
        periodo=periodo_info,
        parametros_alvo=parametros_alvo,
        metricas=metricas,
        series=series,
    )


# ---------- 1) Endpoint JSON (mantém) ----------

@router.get(
    "/relatorios/dispositivos/{dispositivo_id}",
    response_model=RelatorioDispositivoOut,
)
def relatorio_por_dispositivo_json(
    dispositivo_id: str,
    inicio: Optional[datetime] = None,
    fim: Optional[datetime] = None,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_usuario_logado),
):
    return _montar_relatorio_dispositivo(db, dispositivo_id, inicio, fim, current_user)


# ---------- 2) Endpoint PDF ----------

@router.get("/relatorios/dispositivos/{dispositivo_id}/pdf")
def relatorio_por_dispositivo_pdf(
    dispositivo_id: str,
    inicio: Optional[datetime] = None,
    fim: Optional[datetime] = None,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_usuario_logado),
):
    rel = _montar_relatorio_dispositivo(db, dispositivo_id, inicio, fim, current_user)

    buffer = BytesIO()
    c = canvas.Canvas(buffer, pagesize=A4)
    width, height = A4

    y = height - 50

    # Cabeçalho
    c.setFont("Helvetica-Bold", 16)
    c.drawString(50, y, "Relatório do Dispositivo")
    y -= 30

    c.setFont("Helvetica", 10)
    c.drawString(50, y, f"Dispositivo: {rel.dispositivo.get('nome') or rel.dispositivo.get('id')}")
    y -= 15
    c.drawString(50, y, f"Tipo: {rel.dispositivo.get('tipo')}")
    y -= 15
    c.drawString(50, y, f"Lugar: {rel.dispositivo.get('lugar_nome')}")
    y -= 15

    periodo = rel.periodo
    c.drawString(50, y, f"Período: {periodo['inicio']}  até  {periodo['fim']}")
    y -= 25

    # Métricas
    m = rel.metricas
    c.setFont("Helvetica-Bold", 12)
    c.drawString(50, y, "Resumo de umidade")
    y -= 20
    c.setFont("Helvetica", 10)

    c.drawString(50, y, f"Umidade mínima: {m.umidade_min if m.umidade_min is not None else '--'}")
    y -= 15
    c.drawString(50, y, f"Umidade máxima: {m.umidade_max if m.umidade_max is not None else '--'}")
    y -= 15
    c.drawString(50, y, f"Umidade média: {m.umidade_media if m.umidade_media is not None else '--'}")
    y -= 15

    alvo = rel.parametros_alvo
    c.drawString(
        50,
        y,
        f"Faixa alvo: {alvo.get('umidadeMinima', '--')}% a {alvo.get('umidadeMaxima', '--')}%",
    )
    y -= 15

    if m.percentual_dentro_faixa is not None:
        c.drawString(
            50,
            y,
            f"% de leituras dentro da faixa: {m.percentual_dentro_faixa:.1f}%",
        )
        y -= 15

    c.drawString(50, y, f"Total de leituras: {m.leituras_total}")
    y -= 15
    c.drawString(50, y, f"Leituras com umidade: {m.leituras_com_umidade}")
    y -= 25

    # Tabela simples de alguns pontos de umidade
    c.setFont("Helvetica-Bold", 11)
    c.drawString(50, y, "Alguns pontos de umidade (timestamp / %):")
    y -= 20
    c.setFont("Helvetica", 9)

    for ponto in rel.series.umidade[:40]:  # limita pra não explodir uma página
        if y < 50:
            c.showPage()
            y = height - 50
            c.setFont("Helvetica", 9)
        c.drawString(50, y, f"{ponto.timestamp}  -  {ponto.umidade:.1f}%")
        y -= 12

    c.showPage()
    c.save()
    buffer.seek(0)

    filename = f"relatorio_dispositivo_{rel.dispositivo.get('id')}.pdf"

    return StreamingResponse(
        buffer,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


# ---------- 3) Endpoint CSV (Excel abre) ----------

@router.get("/relatorios/dispositivos/{dispositivo_id}/csv")
def relatorio_por_dispositivo_csv(
    dispositivo_id: str,
    inicio: Optional[datetime] = None,
    fim: Optional[datetime] = None,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_usuario_logado),
):
    rel = _montar_relatorio_dispositivo(db, dispositivo_id, inicio, fim, current_user)

    output = StringIO()
    writer = csv.writer(output, delimiter=";")

    # Cabeçalho
    writer.writerow(["Relatório do dispositivo"])
    writer.writerow([f"ID", rel.dispositivo.get("id")])
    writer.writerow([f"Nome", rel.dispositivo.get("nome")])
    writer.writerow([f"Tipo", rel.dispositivo.get("tipo")])
    writer.writerow([f"Lugar", rel.dispositivo.get("lugar_nome")])
    writer.writerow([])

    periodo = rel.periodo
    writer.writerow(["Período", f"{periodo['inicio']} até {periodo['fim']}"])
    writer.writerow([])

    # Métricas
    m = rel.metricas
    alvo = rel.parametros_alvo

    writer.writerow(["Métrica", "Valor"])
    writer.writerow(["Umidade mínima", m.umidade_min])
    writer.writerow(["Umidade máxima", m.umidade_max])
    writer.writerow(["Umidade média", m.umidade_media])
    writer.writerow(
        ["Faixa alvo", f"{alvo.get('umidadeMinima', '--')} a {alvo.get('umidadeMaxima', '--')} %"]
    )
    writer.writerow(
        [
            "% leituras dentro da faixa",
            m.percentual_dentro_faixa if m.percentual_dentro_faixa is not None else "",
        ]
    )
    writer.writerow(["Total de leituras", m.leituras_total])
    writer.writerow(["Leituras com umidade", m.leituras_com_umidade])
    writer.writerow([])

    # Série de umidade
    writer.writerow(["Timestamp", "Umidade (%)"])
    for ponto in rel.series.umidade:
        writer.writerow([ponto.timestamp.isoformat(), ponto.umidade])

    output.seek(0)
    filename = f"relatorio_dispositivo_{rel.dispositivo.get('id')}.csv"

    return StreamingResponse(
        output,
        media_type="text/csv",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )

