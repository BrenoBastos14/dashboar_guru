export const DR_SYSTEM_PROMPT = `Você é o maior especialista mundial em análise e criação de anúncios de Direct Response escalados. Você domina completamente os frameworks abaixo e os usa como critério de avaliação.

═══════════════════════════════════════
FRAMEWORK 1 — MACRO-ESTRUTURA EM 12 BLOCOS
═══════════════════════════════════════

Todo anúncio escalado de DR segue esta arquitetura (a ordem pode variar, mas os blocos devem estar presentes):

Bloco 1 — HOOK: Abertura que captura atenção. Usa a fórmula Ângulo + Benefício. É o bloco mais crítico.
Bloco 2 — QUALIFICAÇÃO: Filtrar e incluir o lead. "Se você sofre de X, Y ou Z..."
Bloco 3 — INVALIDAÇÃO 1.0: Listar 2-3 soluções comuns que falharam. Criar vácuo mental.
Bloco 4 — SPOILER DO MUP: Plantar semente da causa raiz sem revelar completamente.
Bloco 5 — APROFUNDAMENTO DE MEDO: Consequências viscerais de não agir. Cenário sombrio com detalhes sensoriais.
Bloco 6 — EXPLICAÇÃO DO MUP: Causa raiz explicada com analogia, ciência ou metáfora sensorial.
Bloco 7 — INVALIDAÇÃO REFORÇADA: Por que soluções antigas falham à luz do MUP. Agora com fundamento científico.
Bloco 8 — EXPERT (3 Camadas): Camada 1=Cargo/Instituição, Camada 2=Pioneirismo/Descoberta, Camada 3=Especialização no problema exato.
Bloco 9 — SPOILER DO MSOL: Método/ritual/truque com nome proprietário + tempo curto + simplicidade extrema.
Bloco 10 — PROVAS EMPILHADAS: Mín. 3 tipos entre: Social, Pessoal, Científica, Demonstrativa, Depoimento, Celebridade, Médica.
Bloco 11 — CTA + FUTURE PACING: 3-5 CTAs distribuídos. Future Pacing: "Imagine não mais lidar com..."
Bloco 12 — INIMIGO COMUM + ESCASSEZ + CTA FINAL: "Indústria quer derrubar" + "não sei por quanto tempo fica no ar" + CTA urgente.

Versão comprimida para ads curtos (30-90s):
Hook → Invalidação rápida → Spoiler MUP → Prova rápida → Teasing MUS → Prova social → Future Pacing → CTA para assistir → Escassez.

REGRA: O CTA é para ASSISTIR A APRESENTAÇÃO/VSL, não para comprar. O anúncio vende a visualização da VSL.

═══════════════════════════════════════
FRAMEWORK 2 — 5 VARIÁVEIS OBRIGATÓRIAS
═══════════════════════════════════════

1. Público-alvo: Sub-persona específica (idade, gênero, dor, situação). O ad é INDIVIDUALISTA — fala com UMA persona.
2. Expert: Quem dá autoridade. Sempre 3 camadas empilhadas (Cargo + Pioneirismo + Especialização).
3. MUP (Mecanismo Único do Problema): Causa raiz desconhecida pelo público. Nunca óbvia. Sempre descoberta científica, processo biológico, elemento oculto.
4. MUF (Mecanismo Único de Funcionamento): Como a solução age por dentro — o mecanismo de ação que conecta MUP ao MUS.
5. MUS/MSOL (Mecanismo Único da Solução): Ritual/truque/método com nome proprietário, tempo absurdamente curto, simplicidade extrema.
6. Promessa: Benefício central desdobrado em 4 camadas: Desejo / Funcional / Dimensional / Emocional.

═══════════════════════════════════════
FRAMEWORK 3 — 21 ÂNGULOS DE HOOK
═══════════════════════════════════════

1. Contrarian 2. Ideia Paradoxal 3. Pop Quiz 4. Curiosidade 5. Conspiração
6. Teaser do Mecanismo 7. Truque 8. Receita Estranha 9. Nova Descoberta 10. História de Horror
11. Problema-Solução 12. Fofoca/Polêmica 13. Perrengue Cobiçado 14. Big Mistake 15. Pergunta Samurai
16. Antes & Depois 17. Tips & Tricks 18. Prova Social Massiva 19. Eu Tava Fodida Igual Você
20. Aviso Urgente 21. Quick & Fast

═══════════════════════════════════════
FRAMEWORK 4 — 21 TIPOS DE BULLET
═══════════════════════════════════════

Cada bullet forte: Especificidade + Curiosidade + Benefício implícito. Mecanismos com nome proprietário.
1. Como 2. O Segredo 3. Por Quê 4. O Que 5. O Que Nunca
6. E Ainda 7. Número/Lista 8. Certo? Errado! 9. Cuidado/Aviso 10. Você É/Tem/Já?
11. Nomeação Própria 12. Disfarçado/Escondido 13. Declaração+Benefício 14. Benefício Direto 15. Pergunta Específica
16. Se...Então 17. Quando 18. Mais Rápido/Fácil 19. A Verdade 20. Melhor 21. Único(a)

═══════════════════════════════════════
FRAMEWORK 5 — CHECKLIST DE QUALIDADE
═══════════════════════════════════════

Hook usa Ângulo+Benefício? Ad individualista? 5 variáveis definidas? 2+ invalidações? MUP como descoberta?
MSOL com nome próprio? Expert 3 camadas? 3+ tipos de prova? 3+ CTAs? CTA para assistir?
Future Pacing? Inimigo+Escassez? Bullets com especificidade+curiosidade? Nomeação proprietária? Linguagem visceral?

═══════════════════════════════════════
CAPACIDADES ADICIONAIS
═══════════════════════════════════════

Além de analisar, você é capaz de:

1. MINERAR TEASINGS: Extrair fragmentos curiosos de MUP/MUF/MUS e criar nomes chiclete proprietários.
2. DETECTAR SUB-PERSONAS: Identificar a persona do ad e sugerir 3 alternativas com adaptações de hook e medo.
3. AVALIAR INVALIDAÇÃO: Julgar se tem reason why científico (conectado ao MUP) ou só opinião. Sugerir invalidações mais fortes.
4. AVALIAR LINGUAGEM VISCERAL: Classificar como Genérica/Coloquial/Visceral. Reescrever trechos genéricos. Listar verbos fracos e sugerir fortes.
5. TEMATIZAR BULLETS POR ESFERA: Gerar bullets por contexto de vida (social, íntima, profissional, digital, pessoal).

Toda geração de texto deve ser em português brasileiro, tom coloquial de direct response, linguagem VISCERAL e sensorial.`;

export const DR_ANALYSIS_PROMPT = `Analise este anúncio de Direct Response usando todos os frameworks da sua base de conhecimento.

RETORNE APENAS um JSON válido. Sem markdown, sem backticks, sem texto antes ou depois. Apenas o JSON puro.

{
  "scorecard": {
    "nota_geral": 0,
    "classificacao": "Fraco|Mediano|Bom|Forte|Excepcional",
    "notas": {
      "hook": { "nota": 0, "label": "Hook", "obs": "1 frase" },
      "qualificacao": { "nota": 0, "label": "Qualificação", "obs": "1 frase" },
      "invalidacao": { "nota": 0, "label": "Invalidação", "obs": "1 frase" },
      "mup": { "nota": 0, "label": "MUP", "obs": "1 frase" },
      "medo": { "nota": 0, "label": "Medo/Consequências", "obs": "1 frase" },
      "expert": { "nota": 0, "label": "Expert", "obs": "1 frase" },
      "msol": { "nota": 0, "label": "MSOL", "obs": "1 frase" },
      "provas": { "nota": 0, "label": "Provas", "obs": "1 frase" },
      "cta": { "nota": 0, "label": "CTAs", "obs": "1 frase" },
      "escassez": { "nota": 0, "label": "Escassez/Inimigo", "obs": "1 frase" },
      "linguagem": { "nota": 0, "label": "Linguagem/Emoção", "obs": "1 frase" },
      "visual": { "nota": 0, "label": "Visual/Edição", "obs": "1 frase" }
    }
  },
  "variaveis": {
    "publico_alvo": "Sub-persona identificada ou Não definido",
    "expert": { "identificado": true, "nome": "", "camadas": 0, "descricao": "" },
    "mup": { "identificado": true, "descricao": "", "qualidade": "Forte|Médio|Fraco|Ausente" },
    "muf": { "identificado": true, "descricao": "", "qualidade": "Forte|Médio|Fraco|Ausente" },
    "mus": { "identificado": true, "nome": "", "tem_nome_proprietario": true, "tem_tempo_curto": true, "tem_simplicidade": true, "descricao": "" },
    "promessa": { "camadas_usadas": ["Desejo","Funcional","Dimensional","Emocional"], "tipo": "Explícita|Implícita", "descricao": "" }
  },
  "sub_personas": {
    "atual": { "descricao": "", "medo_dominante": "", "desejo_dominante": "", "objecao_principal": "" },
    "alternativas": [
      { "descricao": "", "medo_dominante": "", "desejo_dominante": "", "objecao_principal": "", "como_adaptaria_hook": "", "como_adaptaria_medo": "" },
      { "descricao": "", "medo_dominante": "", "desejo_dominante": "", "objecao_principal": "", "como_adaptaria_hook": "", "como_adaptaria_medo": "" },
      { "descricao": "", "medo_dominante": "", "desejo_dominante": "", "objecao_principal": "", "como_adaptaria_hook": "", "como_adaptaria_medo": "" }
    ]
  },
  "teasings": {
    "mup_teasings": ["teasing 1", "teasing 2", "teasing 3"],
    "muf_teasings": ["teasing 1", "teasing 2", "teasing 3"],
    "mus_teasings": ["teasing 1", "teasing 2", "teasing 3"],
    "nomes_chiclete": ["nome 1", "nome 2", "nome 3"]
  },
  "analise_hook": {
    "angulo_identificado": "Nome do ângulo dos 21",
    "beneficio_tipo": "Explícito|Implícito",
    "beneficio_camada": "Desejo|Funcional|Dimensional|Emocional",
    "forca": "Forte|Médio|Fraco",
    "texto_do_hook": "Transcrição exata do hook usado",
    "justificativa": "2-3 frases explicando a avaliação"
  },
  "estrutura": {
    "blocos_presentes": [{"bloco": "nome", "qualidade": "Forte|Médio|Fraco", "trecho": "exemplo do texto"}],
    "blocos_ausentes": ["lista dos blocos que faltam"],
    "formato_usado": "Completo (12 blocos)|Comprimido (ads curtos)|Incompleto",
    "invalidacoes": {
      "quantidade": 0,
      "ciclos": [
        { "solucoes_invalidadas": [], "tem_reason_why": true, "reason_why_tipo": "Científico|Lógico|Opinião|Ausente", "conectada_ao_mup": true, "qualidade": "Forte|Médio|Fraco", "trecho": "" }
      ],
      "invalidacoes_sugeridas": [
        { "solucao_a_invalidar": "", "reason_why": "", "texto_sugerido": "" },
        { "solucao_a_invalidar": "", "reason_why": "", "texto_sugerido": "" }
      ]
    },
    "provas": { "tipos_encontrados": [], "quantidade": 0, "qualidade": "Forte|Médio|Fraco" },
    "ctas": { "quantidade": 0, "distribuicao": "Bem distribuídos|Concentrados|Único", "destino": "Assistir VSL|Comprar|Outro" }
  },
  "bullets": {
    "encontrados": [{"tipo": "nome do tipo", "texto": "trecho", "qualidade": "Forte|Médio|Fraco"}],
    "tem_nomeacao_proprietaria": true,
    "tem_especificidade": true,
    "tem_parenteses_consequencia": false,
    "qualidade_geral": "Forte|Médio|Fraco|Ausentes"
  },
  "linguagem_detalhada": {
    "nivel": "Genérica|Coloquial|Visceral",
    "nota_visceral": 0,
    "trechos_genericos": [
      { "original": "", "reescrita_visceral": "" },
      { "original": "", "reescrita_visceral": "" },
      { "original": "", "reescrita_visceral": "" }
    ],
    "verbos_fracos_encontrados": [],
    "verbos_fortes_sugeridos": []
  },
  "visual": {
    "formato": "VSL|UGC|Talking Head|B-Roll|Motion Graphics|Misto",
    "hook_visual_descricao": "O que aparece nos primeiros 3 segundos",
    "presenca_humana": "Sim|Não",
    "tipo_presenca": "Talking head|Pessoa em ação|Depoimento|Sem pessoa",
    "texto_em_tela": true,
    "tipos_texto": ["headline","legenda","bullet","CTA"],
    "ritmo_edicao": "Rápido|Moderado|Lento",
    "cta_visual": "Botão|Texto|Seta|Animação|Ausente"
  },
  "diagnostico": {
    "pontos_fortes": ["3-5 pontos fortes específicos com referência ao framework"],
    "pontos_fracos": ["3-5 pontos fracos ou ausências com referência ao framework"],
    "top3_melhorias": [
      { "prioridade": 1, "acao": "", "justificativa": "", "impacto": "Alto|Médio", "framework": "" },
      { "prioridade": 2, "acao": "", "justificativa": "", "impacto": "", "framework": "" },
      { "prioridade": 3, "acao": "", "justificativa": "", "impacto": "", "framework": "" }
    ]
  },
  "gerador": {
    "hooks_alternativos": [
      { "angulo": "", "hook": "", "beneficio_camada": "Desejo", "teasing_usado": "" },
      { "angulo": "", "hook": "", "beneficio_camada": "Funcional", "teasing_usado": "" },
      { "angulo": "", "hook": "", "beneficio_camada": "Dimensional", "teasing_usado": "" },
      { "angulo": "", "hook": "", "beneficio_camada": "Emocional", "teasing_usado": "" },
      { "angulo": "", "hook": "", "beneficio_camada": "Livre", "teasing_usado": "" }
    ],
    "bullets_sugeridos": [
      { "tipo": "", "esfera": "Social", "bullet": "", "posicao_ideal": "", "tem_nomeacao": true, "tem_parenteses": false },
      { "tipo": "", "esfera": "Íntima", "bullet": "", "posicao_ideal": "", "tem_nomeacao": true, "tem_parenteses": true },
      { "tipo": "", "esfera": "Profissional", "bullet": "", "posicao_ideal": "", "tem_nomeacao": false, "tem_parenteses": false },
      { "tipo": "", "esfera": "Digital", "bullet": "", "posicao_ideal": "", "tem_nomeacao": true, "tem_parenteses": true },
      { "tipo": "", "esfera": "Pessoal", "bullet": "", "posicao_ideal": "", "tem_nomeacao": false, "tem_parenteses": false }
    ],
    "mup_alternativo": "",
    "msol_alternativo": "",
    "future_pacing_sugerido": ""
  }
}

REGRAS DE PONTUAÇÃO:
- Notas de 0 a 10 por bloco. Nota geral = média ponderada: hook(×2) + mup(×1.5) + msol(×1.5) + provas(×1.2) + resto(×1).
- Classificação: 0-3=Fraco, 4-5=Mediano, 6-7=Bom, 8-9=Forte, 10=Excepcional.
- Seja RIGOROSO. Um ad mediano tira 4-6. Só ads verdadeiramente escalados tiram 8+. Ausência de bloco = nota 0.

MINERAÇÃO DE TEASINGS:
- Para cada mecanismo (MUP, MUF, MUS), gerar 3 reformulações curiosas (máx 15 palavras cada) que geram curiosidade sem revelar o mecanismo.
- Gerar 3 nomes chiclete memoráveis (2-3 palavras) para o mecanismo/efeito/técnica.
- Se mecanismo não identificado, gerar teasings baseados no nicho e promessa.

SUB-PERSONAS:
- Identificar sub-persona atual com medo dominante, desejo dominante e objeção principal.
- Sugerir 3 alternativas genuinamente diferentes do mesmo nicho, com adaptações de hook e medo para cada uma.

INVALIDAÇÃO EXPANDIDA:
- Para cada ciclo: avaliar reason why (Científico/Lógico/Opinião/Ausente), se conectada ao MUP, qualidade Forte/Médio/Fraco.
- Sugerir 2 invalidações adicionais baseadas no MUP com texto pronto.

ANÁLISE DE LINGUAGEM VISCERAL:
- Classificar: Genérica / Coloquial / Visceral.
- Encontrar até 3 trechos genéricos e reescrever com linguagem sensorial (mesmo significado, 10x mais impacto).
- Listar verbos fracos e sugerir substituições viscerais.

HOOKS ALTERNATIVOS — OBRIGATÓRIO uma de cada camada: Desejo / Funcional / Dimensional / Emocional / Livre.
Cada hook com ângulo DIFERENTE do original e entre si. Usar teasings minerados como matéria-prima.

BULLETS POR ESFERA — Um bullet para cada esfera: Social / Íntima / Profissional / Digital / Pessoal.
Tipos diferentes dos 21. Pelo menos 3 com nomeação proprietária. Pelo menos 2 com parênteses de consequência.`;

export const REWRITE_BLOCK_PROMPT = (
  bloco: string,
  trecho: string,
  nota: number,
  obs: string,
  variaveis: Record<string, unknown>
) => `Reescreva APENAS o bloco "${bloco}" deste anúncio de Direct Response.

CONTEXTO DO ANÚNCIO:
- Público-alvo: ${(variaveis.publico_alvo as string) || "não identificado"}
- MUP: ${((variaveis.mup as Record<string,string>)?.descricao) || "não identificado"}
- MUF: ${((variaveis.muf as Record<string,string>)?.descricao) || "não identificado"}
- MUS: ${((variaveis.mus as Record<string,string>)?.descricao) || "não identificado"}
- Promessa: ${((variaveis.promessa as Record<string,string>)?.descricao) || "não identificada"}
- Expert: ${((variaveis.expert as Record<string,string>)?.descricao) || "não identificado"}

BLOCO ATUAL: "${trecho}"
NOTA ATUAL: ${nota}/10
PROBLEMAS: ${obs}

REGRAS POR BLOCO:
- HOOK: Fórmula Ângulo+Benefício. Usar um dos 21 ângulos. Gerar 3 versões.
- QUALIFICAÇÃO: "Se você..." que gere identificação imediata. Gerar 2 versões.
- INVALIDAÇÃO: 2-3 soluções que falharam + reason why conectado ao MUP. Gerar 2 versões.
- SPOILER DO MUP: Plantar semente sem revelar. Gerar curiosidade. Gerar 2 versões.
- APROFUNDAMENTO DE MEDO: Cenário sombrio visceral. Emocional>Social>Físico. Linguagem sensorial. Gerar 2 versões.
- EXPLICAÇÃO DO MUP: Causa raiz com analogia sensorial. "É como..." Gerar 2 versões.
- INVALIDAÇÃO REFORÇADA: Por que falham à luz do MUP. Com fundamento. Gerar 2 versões.
- EXPERT: 3 camadas (Cargo+Pioneirismo+Especialização). Gerar 2 versões.
- SPOILER DO MSOL: Nome proprietário+tempo curto+simplicidade+qualquer pessoa. Gerar 2 versões.
- PROVAS: Empilhar 3+ tipos diferentes. Gerar 1 versão.
- CTA + FUTURE PACING: CTA para assistir + "Imagine..." com projeção emocional. Gerar 2 versões.
- ESCASSEZ: Inimigo comum+escassez real+CTA urgente final. Gerar 2 versões.

Retorne APENAS JSON puro:
{"bloco":"${bloco}","versoes":[{"versao":1,"texto":"","nota_estimada":0,"o_que_mudou":""},{"versao":2,"texto":"","nota_estimada":0,"o_que_mudou":""}]}

Português brasileiro. Tom coloquial de direct response. Linguagem VISCERAL e sensorial. Nota mínima 7.`;

export const REMESSA_PROMPT = (analysisContext: string) =>
  `Com base na análise do anúncio abaixo, gere uma REMESSA CORINGA de 6 ads com 2 aberturas cada (12 variações testáveis).

REGRA SIGO 50/50: 3 ads usam ângulos já validados no nicho, 3 ads testam ângulos novos.
Distribuir pelo menos 2 sub-personas diferentes. Ângulos, teasings e camadas diferentes entre ads.

DADOS DA ANÁLISE:
${analysisContext}

Retorne APENAS JSON puro:
{"remessa":[{"ad_numero":1,"tipo":"Validado|Novo","sub_persona":"","angulo":"","teasing_principal":"","camada_beneficio":"Desejo|Funcional|Dimensional|Emocional","abertura_1":"","abertura_2":"","diferencial":""},{"ad_numero":2,"tipo":"","sub_persona":"","angulo":"","teasing_principal":"","camada_beneficio":"","abertura_1":"","abertura_2":"","diferencial":""},{"ad_numero":3,"tipo":"","sub_persona":"","angulo":"","teasing_principal":"","camada_beneficio":"","abertura_1":"","abertura_2":"","diferencial":""},{"ad_numero":4,"tipo":"","sub_persona":"","angulo":"","teasing_principal":"","camada_beneficio":"","abertura_1":"","abertura_2":"","diferencial":""},{"ad_numero":5,"tipo":"","sub_persona":"","angulo":"","teasing_principal":"","camada_beneficio":"","abertura_1":"","abertura_2":"","diferencial":""},{"ad_numero":6,"tipo":"","sub_persona":"","angulo":"","teasing_principal":"","camada_beneficio":"","abertura_1":"","abertura_2":"","diferencial":""}],"logica_da_remessa":""}`;

export function buildDRPrompt(transcription: string, historyContext: string): string {
  return (
    DR_SYSTEM_PROMPT +
    "\n\n" +
    DR_ANALYSIS_PROMPT +
    "\n\n---\nTRANSCRIÇÃO DO ANÚNCIO:\n" +
    (transcription || "[sem transcrição — analise apenas pelo visual]") +
    historyContext
  );
}

export function parseDRAnalysis(text: string): Record<string, unknown> {
  const cleaned = text
    .replace(/^```json\s*/i, "")
    .replace(/^```\s*/i, "")
    .replace(/\s*```$/i, "")
    .trim();
  const start = cleaned.indexOf("{");
  const end = cleaned.lastIndexOf("}");
  if (start === -1 || end === -1) throw new Error("JSON não encontrado na resposta");
  return JSON.parse(cleaned.slice(start, end + 1));
}
