import traceback

import pandas as pd
import streamlit as st

from utils.charts import chart_receita_por_periodo
from utils.data_processor import clean_data, compute_kpis, filter_data, load_csv
from utils.facebook_data import (
    aggregate_fb_metrics,
    load_facebook_file,
    merge_fb_guru,
)


# ---------------------------------------------------------------------------
# Configuração da página
# ---------------------------------------------------------------------------
st.set_page_config(
    page_title="Dashboard Guru Manager",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded",
)


def _brl(v):
    """Formata float como moeda BRL. Ex: 1234.5 → 'R$ 1.234,50'"""
    try:
        return "R$ " + f"{float(v):,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
    except (TypeError, ValueError):
        return "R$ 0,00"


def _cell_style(val, vmax):
    """CSS de fundo proporcional ao valor — sem precisar de matplotlib."""
    if vmax == 0 or val == 0:
        return "background-color: #f5f5f5; color: #cccccc"
    intensity = float(val) / float(vmax)
    r = int(255 - (255 - 45)  * intensity)
    g = int(255 - (255 - 125) * intensity)
    b = int(255 - (255 - 70)  * intensity)
    text = "white" if intensity > 0.55 else "#222222"
    return f"background-color: rgb({r},{g},{b}); color: {text}"


def _cell_style_red(val, vmax):
    """CSS heatmap vermelho (para gasto)."""
    if vmax == 0 or val == 0:
        return "background-color: #f5f5f5; color: #cccccc"
    intensity = float(val) / float(vmax)
    r = int(255 - (255 - 220) * intensity)
    g = int(255 - (255 - 38)  * intensity)
    b = int(255 - (255 - 38)  * intensity)
    text = "white" if intensity > 0.55 else "#222222"
    return f"background-color: rgb({r},{g},{b}); color: {text}"


def _resumo_tabela(df, campo, label):
    """Retorna DataFrame agrupado por campo com Vendas e Receita (R$)."""
    grp = df[df[campo].notna()].groupby(campo)["valor"]
    tbl = pd.concat(
        [grp.count().rename("Vendas"), grp.sum().rename("Receita (R$)")],
        axis=1,
    ).sort_values("Receita (R$)", ascending=False).reset_index()
    tbl["Receita (R$)"] = tbl["Receita (R$)"].apply(_brl)
    return tbl.rename(columns={campo: label})


# ---------------------------------------------------------------------------
# Sidebar — upload
# ---------------------------------------------------------------------------
with st.sidebar:
    st.image(
        "https://img.icons8.com/color/96/combo-chart--v1.png",
        width=60,
    )
    st.title("Guru Manager")
    st.caption("Dashboard de Vendas")
    st.divider()

    uploaded_file = st.file_uploader(
        "Carregar CSV ou Excel (Guru)",
        type=["csv", "xlsx"],
        help="Exporte o relatório de vendas no Guru Manager e faça upload aqui (.csv ou .xlsx).",
    )

    uploaded_fb = st.file_uploader(
        "Carregar CSV ou Excel (Facebook Ads)",
        type=["csv", "xlsx"],
        help="Exporte o relatório de gastos do Facebook Ads e faça upload aqui.",
    )

    st.divider()
    st.subheader("Filtros")

# ---------------------------------------------------------------------------
# Tabs principais
# ---------------------------------------------------------------------------
tab_guru, tab_fb, tab_video = st.tabs([
    "📊 Vendas Guru Manager",
    "📱 Facebook Ads",
    "🎬 Video Cutter",
])

# ===========================================================================
# TAB 3 — Video Cutter (cortes automáticos por fala)
# Renderizado antes das outras tabs para não ser bloqueado por st.stop()
# do tab_guru/tab_fb quando não há upload de CSV.
# ===========================================================================
with tab_video:
    import hashlib
    import json as _json
    import shutil as _shutil
    import tempfile
    from pathlib import Path as _Path

    from utils.charts import chart_topic_timeline
    from utils.clipper import build_output_zip, render_clips
    from utils.topic_segmenter import segment_topics
    from utils.transcription import (
        transcribe_all,
        transcript_to_srt,
        transcript_to_vtt,
    )
    from utils.video import (
        FFmpegError,
        chunk_audio,
        extract_audio,
        probe_duration,
    )

    def _render_video_tab():
        st.markdown("## 🎬 Video Cutter — Cortes por fala")
        st.caption(
            "Faça upload de um vídeo (até 2h) e a ferramenta transcreve a fala, "
            "identifica tópicos e gera clipes curtos independentes. "
            "Recomendação: vídeos acima de 500 MB podem estourar memória/disco do "
            "servidor — exporte em 720p h264 antes."
        )

        # Gates de ambiente
        _api_key = st.secrets.get("OPENAI_API_KEY") if hasattr(st, "secrets") else None
        if not _api_key:
            st.error(
                "Configure **OPENAI_API_KEY** em Settings → Secrets (ou "
                "`.streamlit/secrets.toml` local) para usar este recurso."
            )
            return
        if _shutil.which("ffmpeg") is None:
            st.error(
                "ffmpeg não encontrado no servidor. "
                "Confirme que o deploy instalou o pacote (nixpacks.toml)."
            )
            return

        ss = st.session_state
        ss.setdefault("vc_workdir", None)
        ss.setdefault("vc_video_hash", None)
        ss.setdefault("vc_video_path", None)
        ss.setdefault("vc_duration", 0.0)
        ss.setdefault("vc_transcript", None)
        ss.setdefault("vc_topics", None)
        ss.setdefault("vc_outputs", None)
        ss.setdefault("vc_done", False)

        uploaded_video = st.file_uploader(
            "Vídeo (mp4, mov, mkv, webm)",
            type=["mp4", "mov", "mkv", "webm"],
            key="vc_upload",
        )

        col_a, col_b, col_c, col_d = st.columns(4)
        with col_a:
            lang = st.selectbox(
                "Idioma da fala",
                options=["auto", "pt", "en", "es"],
                index=1,
                help="'auto' deixa o Whisper detectar.",
            )
        with col_b:
            min_clip = st.slider("Clip mín (s)", 15, 300, 30, step=5)
        with col_c:
            max_clip = st.slider("Clip máx (s)", 60, 600, 180, step=15)
        with col_d:
            target_n = st.slider("Nº alvo de clipes", 0, 20, 0, help="0 = sem alvo")

        if uploaded_video is not None:
            size_mb = uploaded_video.size / (1024 * 1024)
            with st.expander("🔍 Diagnóstico — arquivo e estimativa de custo", expanded=False):
                st.write(f"**Arquivo:** {uploaded_video.name} · {size_mb:,.1f} MB")
                st.caption(
                    "Estimativa só é precisa após a extração do áudio (próximo passo). "
                    "Whisper API: ~US$ 0.006/min. LLM de segmentação: ~US$ 0.02–0.10 por vídeo."
                )

        go = st.button(
            "🚀 Processar vídeo",
            type="primary",
            disabled=uploaded_video is None,
            use_container_width=True,
        )

        if go and uploaded_video is not None:
            try:
                raw = uploaded_video.getvalue()
                video_hash = hashlib.md5(raw).hexdigest()[:12]

                if ss["vc_video_hash"] != video_hash:
                    old = ss.get("vc_workdir")
                    if old and _Path(old).exists():
                        _shutil.rmtree(old, ignore_errors=True)
                    ss["vc_workdir"] = tempfile.mkdtemp(prefix="vc_")
                    ss["vc_video_hash"] = video_hash
                    ss["vc_transcript"] = None
                    ss["vc_topics"] = None
                    ss["vc_outputs"] = None
                    ss["vc_done"] = False

                workdir = _Path(ss["vc_workdir"])
                video_path = workdir / f"source_{video_hash}{_Path(uploaded_video.name).suffix}"

                if not video_path.exists():
                    with open(video_path, "wb") as f:
                        f.write(raw)
                ss["vc_video_path"] = str(video_path)

                with st.status("Processando vídeo…", expanded=True) as status:
                    st.write("🕒 Lendo duração do vídeo…")
                    duration = probe_duration(str(video_path))
                    ss["vc_duration"] = duration
                    st.write(f"   Duração: **{duration/60:.1f} min**.")

                    audio_path = workdir / "audio.mp3"
                    if not audio_path.exists():
                        st.write("🎧 Extraindo áudio (mp3 mono 16 kHz)…")
                        extract_audio(str(video_path), str(audio_path))

                    chunks_dir = workdir / "chunks"
                    chunks_dir.mkdir(exist_ok=True)
                    existing_chunks = sorted(chunks_dir.glob("chunk_*.mp3"))
                    if not existing_chunks:
                        st.write("✂️ Dividindo áudio em pedaços de 10 min…")
                        chunks_meta = chunk_audio(str(audio_path), str(chunks_dir))
                    else:
                        chunks_meta = []
                        offset = 0.0
                        for p in existing_chunks:
                            dur = probe_duration(str(p))
                            chunks_meta.append({
                                "path": str(p),
                                "start_offset": offset,
                                "duration": dur,
                            })
                            offset += dur
                    st.write(f"   {len(chunks_meta)} pedaço(s) de áudio.")

                    if ss["vc_transcript"] is None:
                        st.write("🗣️ Transcrevendo via Whisper API…")
                        progress_trans = st.progress(0.0, text="0 / ?")

                        def _cb(i, n):
                            progress_trans.progress(i / max(n, 1), text=f"{i} / {n}")

                        transcript = transcribe_all(
                            chunks_meta,
                            api_key=_api_key,
                            language=lang if lang != "auto" else None,
                            progress_cb=_cb,
                        )
                        transcript["duration"] = transcript.get("duration") or duration
                        ss["vc_transcript"] = transcript
                    else:
                        st.write("🗣️ Transcrição reutilizada do processamento anterior.")
                    transcript = ss["vc_transcript"]
                    st.write(f"   {len(transcript.get('segments') or [])} segmentos transcritos.")

                    st.write("🧠 Identificando tópicos e clipes…")
                    topics = segment_topics(
                        transcript,
                        api_key=_api_key,
                        min_clip_sec=min_clip,
                        max_clip_sec=max_clip,
                        target_n=target_n or None,
                    )
                    if not topics:
                        status.update(label="Nenhum clipe identificado", state="error")
                        st.warning(
                            "O LLM não identificou clipes viáveis. Tente reduzir o "
                            "tamanho mínimo ou usar um vídeo com fala mais estruturada."
                        )
                        return
                    ss["vc_topics"] = topics
                    st.write(f"   {len(topics)} clipe(s) definido(s).")

                    st.write("🎞️ Renderizando clipes (ffmpeg)…")
                    progress_render = st.progress(0.0, text=f"0 / {len(topics)}")

                    def _cb2(i, n):
                        progress_render.progress(i / max(n, 1), text=f"{i} / {n}")

                    clips_dir = workdir / "clips"
                    if clips_dir.exists():
                        _shutil.rmtree(clips_dir)
                    render = render_clips(
                        str(video_path), topics, str(clips_dir), progress_cb=_cb2,
                    )

                    st.write("📦 Gerando SRT/VTT e zip…")
                    srt_text = transcript_to_srt(transcript)
                    vtt_text = transcript_to_vtt(transcript)
                    chapters_json = _json.dumps(
                        {
                            "video": uploaded_video.name,
                            "duration": duration,
                            "language": transcript.get("language"),
                            "topics": topics,
                        },
                        ensure_ascii=False,
                        indent=2,
                    )
                    zip_path = workdir / "outputs.zip"
                    build_output_zip(
                        str(zip_path),
                        render["clips"],
                        render["final"],
                        srt_text,
                        vtt_text,
                        chapters_json,
                    )

                    ss["vc_outputs"] = {
                        "clips": render["clips"],
                        "final": render["final"],
                        "srt": srt_text,
                        "vtt": vtt_text,
                        "chapters_json": chapters_json,
                        "zip": str(zip_path),
                    }
                    ss["vc_done"] = True
                    status.update(label="✅ Vídeo processado", state="complete")

            except FFmpegError as e:
                st.error(f"Falha no ffmpeg: {e}")
            except Exception as e:
                st.error(f"Erro ao processar o vídeo: {e}")
                st.code(traceback.format_exc(), language="python")

        if ss.get("vc_done") and ss.get("vc_topics"):
            topics = ss["vc_topics"]
            outputs = ss["vc_outputs"]
            st.divider()
            st.subheader(f"Resultados · {len(topics)} clipe(s)")

            st.plotly_chart(
                chart_topic_timeline(topics, ss.get("vc_duration") or 0.0),
                use_container_width=True,
            )

            for i, t in enumerate(topics):
                with st.expander(
                    f"**{i+1:02d}. {t['title']}** · {t['end']-t['start']:.0f}s "
                    f"({int(t['start']//60):02d}:{int(t['start']%60):02d} → "
                    f"{int(t['end']//60):02d}:{int(t['end']%60):02d})",
                    expanded=False,
                ):
                    if t.get("summary"):
                        st.write(t["summary"])
                    clip_path = outputs["clips"][i] if i < len(outputs["clips"]) else None
                    if clip_path and _Path(clip_path).exists():
                        st.video(clip_path)
                        with open(clip_path, "rb") as f:
                            st.download_button(
                                f"⬇️ Baixar clipe {i+1}",
                                data=f.read(),
                                file_name=_Path(clip_path).name,
                                mime="video/mp4",
                                key=f"dl_clip_{i}",
                            )

            st.divider()
            d1, d2, d3, d4, d5 = st.columns(5)
            if outputs.get("final") and _Path(outputs["final"]).exists():
                with open(outputs["final"], "rb") as f:
                    d1.download_button(
                        "🎬 Vídeo final",
                        data=f.read(),
                        file_name="final.mp4",
                        mime="video/mp4",
                    )
            d2.download_button(
                "📝 SRT",
                data=outputs["srt"],
                file_name="transcript.srt",
                mime="text/plain",
            )
            d3.download_button(
                "📝 VTT",
                data=outputs["vtt"],
                file_name="transcript.vtt",
                mime="text/vtt",
            )
            d4.download_button(
                "🗂️ chapters.json",
                data=outputs["chapters_json"],
                file_name="chapters.json",
                mime="application/json",
            )
            if outputs.get("zip") and _Path(outputs["zip"]).exists():
                with open(outputs["zip"], "rb") as f:
                    d5.download_button(
                        "📦 Tudo (zip)",
                        data=f.read(),
                        file_name="video_cutter_outputs.zip",
                        mime="application/zip",
                    )

    _render_video_tab()


# ===========================================================================
# TAB 1 — Guru Manager
# ===========================================================================
with tab_guru:
    if uploaded_file is None:
        st.markdown("## 📊 Dashboard de Vendas — Guru Manager")
        st.info(
            "**Para começar, faça upload do arquivo CSV** exportado do Guru Manager "
            "usando o painel lateral à esquerda.\n\n"
            "**Como exportar?**\n"
            "1. Acesse o painel do Guru Manager\n"
            "2. Vá em **Relatórios → Vendas**\n"
            "3. Aplique os filtros desejados\n"
            "4. Clique em **Exportar CSV**\n"
            "5. Faça upload do arquivo aqui",
            icon="💡",
        )
        st.stop()

    # -----------------------------------------------------------------------
    # Carrega e processa dados
    # -----------------------------------------------------------------------
    try:
        df_raw = load_csv(uploaded_file)
        df = clean_data(df_raw)
    except Exception as e:
        st.error(f"Erro ao processar o arquivo: {e}")
        st.code(traceback.format_exc(), language="python")
        st.stop()

    if df.empty:
        st.warning("O arquivo CSV está vazio ou não contém dados válidos.")
        st.stop()

    # Diagnóstico
    with st.expander("🔍 Diagnóstico — colunas detectadas no CSV", expanded=False):
        st.write(f"**Linhas carregadas:** {len(df):,}")
        st.write(f"**Colunas detectadas:** {list(df.columns)}")
        st.write(f"**`valor` presente:** {'Sim ✅' if 'valor' in df.columns else 'Não ❌'}")
        if "valor" in df.columns:
            st.write(f"**Amostra de valores:** {df['valor'].head(5).tolist()}")
        st.dataframe(df_raw.head(3), use_container_width=True)

    # -----------------------------------------------------------------------
    # Filtros na sidebar
    # -----------------------------------------------------------------------
    with st.sidebar:
        st.markdown("**Período**")
        if "data" in df.columns:
            min_date = df["data"].min().date()
            max_date = df["data"].max().date()
            start_date = st.date_input("Data inicial", value=min_date, min_value=min_date, max_value=max_date)
            end_date = st.date_input("Data final", value=max_date, min_value=min_date, max_value=max_date)
        else:
            st.caption("Coluna de data não detectada no CSV.")
            start_date = end_date = None

        st.divider()
        status_opts = sorted(df["status"].dropna().unique().tolist()) if "status" in df.columns else []
        selected_status = st.multiselect("Status", options=status_opts, default=status_opts)

        produto_opts = sorted(df["produto"].dropna().unique().tolist()) if "produto" in df.columns else []
        selected_produtos = st.multiselect("Produto", options=produto_opts, default=produto_opts)

        _utm_filtros = [
            ("origem_3",    "Origem 3"),
            ("utm_source",  "UTM Source"),
            ("utm_campaign","UTM Campaign"),
            ("utm_medium",  "UTM Medium"),
            ("utm_content", "UTM Content"),
        ]
        _utm_has_any = any(c in df.columns for c, _ in _utm_filtros)
        if _utm_has_any:
            st.divider()
            st.markdown("**Origem / UTM**")

        utm_selected = {}
        for campo, label in _utm_filtros:
            if campo in df.columns:
                opts = sorted(df[campo].dropna().unique().tolist())
                utm_selected[campo] = st.multiselect(label, options=opts, default=opts)
            else:
                utm_selected[campo] = None

        if "data" in df.columns:
            st.divider()
            agrupamento = st.radio(
                "Agrupar receita por",
                options=["D", "W", "ME"],
                format_func=lambda x: {"D": "Dia", "W": "Semana", "ME": "Mês"}[x],
                horizontal=True,
                index=0,
            )
        else:
            agrupamento = "D"

    # -----------------------------------------------------------------------
    # Aplica filtros
    # -----------------------------------------------------------------------
    df_filtered = filter_data(
        df,
        start_date=start_date,
        end_date=end_date,
        status_list=selected_status if selected_status else None,
        produtos_list=selected_produtos if selected_produtos else None,
        origem_3_list=utm_selected.get("origem_3") or None,
        utm_source_list=utm_selected.get("utm_source") or None,
        utm_campaign_list=utm_selected.get("utm_campaign") or None,
        utm_medium_list=utm_selected.get("utm_medium") or None,
        utm_content_list=utm_selected.get("utm_content") or None,
    )

    # -----------------------------------------------------------------------
    # Header + KPIs
    # -----------------------------------------------------------------------
    st.markdown("## 📊 Dashboard de Vendas — Guru Manager")

    kpis = compute_kpis(df_filtered)

    k1, k2, k3 = st.columns(3)
    k1.metric("Volume de Vendas", f"{kpis['num_vendas']:,}")
    k2.metric("Receita Total", _brl(kpis["receita_total"]))
    k3.metric("Ticket Médio", _brl(kpis["ticket_medio"]))

    st.divider()

    # -----------------------------------------------------------------------
    # Gráfico: Receita por Período
    # -----------------------------------------------------------------------
    st.plotly_chart(
        chart_receita_por_periodo(df_filtered, agrupamento),
        use_container_width=True,
    )

    st.divider()

    # -----------------------------------------------------------------------
    # Status por Dia
    # -----------------------------------------------------------------------
    if (
        "status" in df_filtered.columns
        and "data" in df_filtered.columns
        and "valor" in df_filtered.columns
        and not df_filtered.empty
    ):
        st.subheader("Status por Dia")
        metrica_st = st.radio(
            "Métrica",
            ["Nº de Vendas", "Receita (R$)"],
            horizontal=True,
            key="radio_status_dia",
        )
        use_count_st = metrica_st == "Nº de Vendas"

        df_st = df_filtered.copy()
        df_st["_dia"] = df_st["data"].dt.date

        pivot_st = df_st.pivot_table(
            index="status",
            columns="_dia",
            values="valor",
            aggfunc="count" if use_count_st else "sum",
            fill_value=0,
        )
        pivot_st = pivot_st.sort_index(axis=1)
        pivot_st.columns = [pd.Timestamp(d).strftime("%d/%m") for d in pivot_st.columns]
        pivot_st.index.name = "Status"

        pivot_st = pivot_st.loc[pivot_st.sum(axis=1).sort_values(ascending=False).index]

        if use_count_st:
            pivot_st = pivot_st.astype(int)
        vmax_st = float(pivot_st.values.max()) if pivot_st.values.max() > 0 else 1.0
        styled_st = pivot_st.style.map(lambda v: _cell_style(v, vmax_st))
        if use_count_st:
            styled_st = styled_st.format("{:d}")
        else:
            styled_st = styled_st.format(lambda v: _brl(v) if v > 0 else "—")

        st.dataframe(styled_st, use_container_width=True)
        st.divider()

    # -----------------------------------------------------------------------
    # Resumo por Produto
    # -----------------------------------------------------------------------
    if "produto" in df_filtered.columns and "valor" in df_filtered.columns:
        st.subheader("Resumo por Produto")
        tbl_produto = _resumo_tabela(df_filtered, "produto", "Produto")
        st.dataframe(tbl_produto, use_container_width=True, hide_index=True)
        st.divider()

    # -----------------------------------------------------------------------
    # Resumo por Origem / UTM
    # -----------------------------------------------------------------------
    _utm_resumo = [
        ("origem_3",    "Origem 3"),
        ("utm_source",  "UTM Source"),
        ("utm_campaign","UTM Campaign"),
        ("utm_medium",  "UTM Medium"),
        ("utm_content", "UTM Content"),
    ]
    campos_resumo = [
        (c, l) for c, l in _utm_resumo
        if c in df_filtered.columns and "valor" in df_filtered.columns
    ]

    if campos_resumo:
        st.subheader("Resumo por Origem / UTM")
        for i in range(0, len(campos_resumo), 2):
            cols = st.columns(2)
            for j, (campo, label) in enumerate(campos_resumo[i:i+2]):
                with cols[j]:
                    st.markdown(f"**{label}**")
                    st.dataframe(
                        _resumo_tabela(df_filtered, campo, label),
                        use_container_width=True,
                        hide_index=True,
                    )
        st.divider()

    # -----------------------------------------------------------------------
    # Pivot: Vendas por Dia × Origem / UTM
    # -----------------------------------------------------------------------
    _pivot_campos = [
        ("origem_3",    "Origem 3"),
        ("utm_source",  "UTM Source"),
        ("utm_campaign","UTM Campaign"),
        ("utm_medium",  "UTM Medium"),
        ("utm_content", "UTM Content"),
    ]
    campos_pivot = [
        (c, l) for c, l in _pivot_campos
        if c in df_filtered.columns
        and df_filtered[c].notna().any()
        and "valor" in df_filtered.columns
        and "data" in df_filtered.columns
    ]

    if campos_pivot:
        st.subheader("Distribuição por Dia")
        metrica_pv = st.radio(
            "Métrica",
            ["Nº de Vendas", "Receita (R$)"],
            horizontal=True,
            key="radio_pivot",
        )
        use_count = metrica_pv == "Nº de Vendas"
        has_status = "status" in df_filtered.columns

        for campo, label in campos_pivot:
            df_tmp = df_filtered[df_filtered[campo].notna()].copy()
            df_tmp["_dia"] = df_tmp["data"].dt.date

            idx = [campo, "status"] if has_status else [campo]

            pivot = df_tmp.pivot_table(
                index=idx,
                columns="_dia",
                values="valor",
                aggfunc="count" if use_count else "sum",
                fill_value=0,
            )
            pivot = pivot.sort_index(axis=1)
            pivot.columns = [pd.Timestamp(d).strftime("%d/%m") for d in pivot.columns]
            pivot.index.names = [label, "Status"] if has_status else [label]

            if has_status:
                level0_order = (
                    pivot.groupby(level=0).sum().sum(axis=1)
                    .sort_values(ascending=False).index
                )
                pivot = pivot.loc[level0_order]
            else:
                pivot = pivot.loc[pivot.sum(axis=1).sort_values(ascending=False).index]

            if use_count:
                pivot = pivot.astype(int)
            vmax = float(pivot.values.max()) if pivot.values.max() > 0 else 1.0
            styled = pivot.style.map(lambda v: _cell_style(v, vmax))
            if use_count:
                styled = styled.format("{:d}")
            else:
                styled = styled.format(lambda v: _brl(v) if v > 0 else "—")

            with st.expander(f"**{label}**", expanded=True):
                st.dataframe(styled, use_container_width=True)

        st.divider()

    # -----------------------------------------------------------------------
    # Tabela de Transações
    # -----------------------------------------------------------------------
    st.subheader("Transações Detalhadas")

    display_cols = [c for c in [
        "data", "codigo", "contato", "produto", "valor", "metodo_pagamento", "status",
        "origem_3", "utm_source", "utm_campaign", "utm_medium", "utm_content",
    ] if c in df_filtered.columns]

    col_labels = {
        "data": "Data",
        "codigo": "Código",
        "contato": "Cliente",
        "produto": "Produto",
        "valor": "Valor (R$)",
        "metodo_pagamento": "Pagamento",
        "status": "Status",
        "origem_3": "Origem 3",
        "utm_source": "UTM Source",
        "utm_campaign": "UTM Campaign",
        "utm_medium": "UTM Medium",
        "utm_content": "UTM Content",
    }

    df_display = df_filtered[display_cols].copy()
    if "data" in df_display.columns:
        df_display["data"] = df_display["data"].dt.strftime("%d/%m/%Y %H:%M")
    if "valor" in df_display.columns:
        df_display["valor"] = df_display["valor"].apply(_brl)

    df_display = df_display.rename(columns=col_labels)

    st.dataframe(
        df_display,
        use_container_width=True,
        hide_index=True,
        height=600,
    )

    st.caption(f"Total de {len(df_filtered):,} registros exibidos.")


# ===========================================================================
# TAB 2 — Facebook Ads
# ===========================================================================
with tab_fb:
    st.markdown("## 📱 Facebook Ads — Análise de Gastos e ROAS")

    if uploaded_fb is None:
        st.info(
            "**Faça upload do relatório de gastos do Facebook Ads** usando o painel lateral.\n\n"
            "**Como exportar?**\n"
            "1. Acesse o **Gerenciador de Anúncios** do Facebook\n"
            "2. Vá em **Relatórios → Relatório Personalizado**\n"
            "3. Adicione as colunas: *Nome da campanha, Nome do conjunto, Nome do anúncio, "
            "Hora do dia, Valor usado (BRL), Início dos relatórios*\n"
            "4. Exporte como CSV ou Excel\n"
            "5. Faça upload aqui",
            icon="💡",
        )
        if uploaded_file is None:
            st.warning("Faça também o upload do arquivo de vendas do Guru Manager para cruzar os dados.")
        st.stop()

    # -----------------------------------------------------------------------
    # Carrega arquivo FB
    # -----------------------------------------------------------------------
    try:
        df_fb = load_facebook_file(uploaded_fb)
    except Exception as e:
        st.error(f"Erro ao processar o arquivo do Facebook Ads: {e}")
        st.code(traceback.format_exc(), language="python")
        st.stop()

    if df_fb.empty:
        st.warning("O arquivo do Facebook Ads está vazio ou não contém dados válidos.")
        st.stop()

    with st.expander("🔍 Diagnóstico — colunas detectadas (Facebook Ads)", expanded=False):
        st.write(f"**Linhas carregadas:** {len(df_fb):,}")
        st.write(f"**Colunas detectadas:** {list(df_fb.columns)}")
        hora_ok = "hora" in df_fb.columns and df_fb["hora"].notna().any()
        st.write(f"**`hora` detectada:** {'Sim ✅' if hora_ok else 'Não ❌ — coluna Hora do dia não encontrada no arquivo'}")
        if hora_ok:
            st.write(f"**Amostra de horas:** {df_fb['hora'].dropna().unique()[:10].tolist()}")
        st.write(f"**`gasto` detectado:** {'Sim ✅' if 'gasto' in df_fb.columns else 'Não ❌'}")
        if "gasto" in df_fb.columns:
            st.write(f"**Amostra de gastos:** {df_fb['gasto'].head(5).tolist()}")
        st.dataframe(df_fb.head(5), use_container_width=True)

    # -----------------------------------------------------------------------
    # Filtro de período — Facebook Ads
    # -----------------------------------------------------------------------
    if "data" in df_fb.columns and df_fb["data"].notna().any():
        fb_min = df_fb["data"].min().date()
        fb_max = df_fb["data"].max().date()
        fb_col1, fb_col2 = st.columns(2)
        fb_start = fb_col1.date_input("De (FB)", value=fb_min, min_value=fb_min, max_value=fb_max, key="fb_start")
        fb_end   = fb_col2.date_input("Até (FB)", value=fb_max, min_value=fb_min, max_value=fb_max, key="fb_end")
        df_fb = df_fb[
            (df_fb["data"].dt.date >= fb_start) &
            (df_fb["data"].dt.date <= fb_end)
        ]

    # -----------------------------------------------------------------------
    # KPIs Facebook
    # -----------------------------------------------------------------------
    total_gasto = df_fb["gasto"].sum() if "gasto" in df_fb.columns else 0.0
    st.metric("Total Gasto (FB Ads)", _brl(total_gasto))

    hora_disponivel = "hora" in df_fb.columns and df_fb["hora"].notna().any()

    if not hora_disponivel:
        st.warning(
            "**Coluna de hora não encontrada no arquivo.**\n\n"
            "Para ver métricas por hora, exporte o relatório com a quebra **'Hora do dia'** "
            "ativada no Gerenciador de Anúncios."
        )

    st.divider()

    # -----------------------------------------------------------------------
    # Pivot: Campanha / Conjunto / Anúncio × Hora do Dia — apenas Gasto
    # -----------------------------------------------------------------------
    nivel = st.radio(
        "Visualizar por",
        ["Campanha", "Conjunto de Anúncios", "Anúncio"],
        horizontal=True,
    )

    nivel_col_map = {
        "Campanha": "campanha",
        "Conjunto de Anúncios": "conjunto",
        "Anúncio": "anuncio",
    }
    row_col = nivel_col_map[nivel]

    if row_col not in df_fb.columns:
        st.warning(f"Coluna '{nivel}' não encontrada no arquivo.")
    elif not hora_disponivel:
        # Sem hora: tabela simples de gasto por nível
        tbl_simples = (
            df_fb.groupby(row_col)["gasto"]
            .sum()
            .reset_index()
            .sort_values("gasto", ascending=False)
        )
        tbl_simples["gasto"] = tbl_simples["gasto"].apply(_brl)
        tbl_simples.columns = [nivel, "Gasto (R$)"]
        st.dataframe(tbl_simples, use_container_width=True, hide_index=True)
    else:
        df_pv = df_fb[[row_col, "hora", "gasto"]].dropna(subset=["hora"]).copy()
        df_pv["hora"] = df_pv["hora"].astype(int)

        pivot = df_pv.pivot_table(
            index=row_col,
            columns="hora",
            values="gasto",
            aggfunc="sum",
            fill_value=0,
        )
        # Renomear colunas para "00h", "01h", ...
        pivot.columns = [f"{int(h):02d}h" for h in pivot.columns]
        pivot.index.name = nivel
        # Ordenar linhas por total de gasto
        pivot = pivot.loc[pivot.sum(axis=1).sort_values(ascending=False).index]
        # Adicionar coluna de total
        pivot["Total"] = pivot.sum(axis=1)

        vmax = float(pivot.drop(columns="Total").values.max()) if pivot.shape[1] > 1 else 1.0

        def _style_cell(v):
            if v == 0:
                return "background-color: #f5f5f5; color: #cccccc"
            return _cell_style_red(v, vmax)

        styled = pivot.style.map(
            lambda v: _style_cell(v),
            subset=[c for c in pivot.columns if c != "Total"],
        ).format(lambda v: _brl(v) if v > 0 else "—")

        st.dataframe(styled, use_container_width=True)

    # -----------------------------------------------------------------------
    # Pivot: Gasto por Campanha × Dia (sem cruzamento Guru)
    # -----------------------------------------------------------------------
    if "campanha" in df_fb.columns and "data" in df_fb.columns:
        st.divider()
        st.subheader("Gasto por Campanha × Dia")
        df_pv2 = df_fb.copy()
        df_pv2["_dia"] = pd.to_datetime(df_pv2["data"]).dt.strftime("%d/%m")

        pivot2 = df_pv2.pivot_table(
            index="campanha",
            columns="_dia",
            values="gasto",
            aggfunc="sum",
            fill_value=0,
        )
        pivot2.index.name = "Campanha"
        pivot2 = pivot2.loc[pivot2.sum(axis=1).sort_values(ascending=False).index]
        pivot2["Total"] = pivot2.sum(axis=1)

        vmax2 = float(pivot2.drop(columns="Total").values.max()) if pivot2.shape[1] > 1 else 1.0
        styled2 = pivot2.style.map(
            lambda v: _cell_style_red(v, vmax2),
            subset=[c for c in pivot2.columns if c != "Total"],
        ).format(lambda v: _brl(v) if v > 0 else "—")
        st.dataframe(styled2, use_container_width=True)
