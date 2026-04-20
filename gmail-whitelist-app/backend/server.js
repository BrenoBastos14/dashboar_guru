/**
 * Gmail Whitelist API
 *
 * Servidor que cria filtros no Gmail do usuário via OAuth 2.0
 * para garantir que emails de um remetente específico sejam
 * marcados como importantes e nunca vão para spam.
 */

require('dotenv').config();
const express = require('express');
const { google } = require('googleapis');
const cors = require('cors');
const path = require('path');

const app = express();

// Middlewares
app.use(cors());
app.use(express.json());
app.use(express.static(path.join(__dirname, '..', 'frontend')));

// ===========================================
// CONFIGURAÇÃO DO OAUTH2
// ===========================================

const oauth2Client = new google.auth.OAuth2(
  process.env.GOOGLE_CLIENT_ID,
  process.env.GOOGLE_CLIENT_SECRET,
  `${process.env.BASE_URL}/api/gmail/callback`
);

// Escopos necessários para criar filtros
const SCOPES = [
  'https://www.googleapis.com/auth/gmail.settings.basic'
];

// ===========================================
// ROTAS DA API
// ===========================================

/**
 * Rota inicial - Serve a página principal
 */
app.get('/', (req, res) => {
  res.sendFile(path.join(__dirname, '..', 'frontend', 'index.html'));
});

/**
 * Rota: Iniciar processo de autorização
 *
 * Redireciona o usuário para a tela de login do Google
 */
app.get('/api/gmail/autorizar', (req, res) => {
  const authUrl = oauth2Client.generateAuthUrl({
    access_type: 'offline',
    scope: SCOPES,
    prompt: 'consent', // Força mostrar tela de permissão
    // Você pode passar state para rastrear de onde veio o usuário
    state: req.query.source || 'direct'
  });

  console.log('🔐 Redirecionando usuário para autorização Google...');
  res.redirect(authUrl);
});

/**
 * Rota: Callback após autorização do Google
 *
 * Google redireciona para cá após o usuário autorizar.
 * Aqui trocamos o código por token e criamos o filtro.
 */
app.get('/api/gmail/callback', async (req, res) => {
  const { code, error, state } = req.query;

  // Verificar se houve erro na autorização
  if (error) {
    console.error('❌ Erro na autorização:', error);
    return res.redirect(process.env.ERROR_REDIRECT_URL + '?error=auth_denied');
  }

  // Verificar se recebemos o código
  if (!code) {
    console.error('❌ Código de autorização não recebido');
    return res.redirect(process.env.ERROR_REDIRECT_URL + '?error=no_code');
  }

  try {
    console.log('🔄 Trocando código por token de acesso...');

    // Trocar código por tokens
    const { tokens } = await oauth2Client.getToken(code);
    oauth2Client.setCredentials(tokens);

    // Criar cliente Gmail
    const gmail = google.gmail({ version: 'v1', auth: oauth2Client });

    // Verificar se já existe um filtro para esse remetente
    console.log('🔍 Verificando filtros existentes...');
    const existingFilters = await gmail.users.settings.filters.list({
      userId: 'me'
    });

    const senderEmail = process.env.SENDER_EMAIL;
    const filterExists = existingFilters.data.filter?.some(
      f => f.criteria?.from?.toLowerCase() === senderEmail.toLowerCase()
    );

    if (filterExists) {
      console.log('ℹ️ Filtro já existe para:', senderEmail);
      return res.redirect(process.env.SUCCESS_REDIRECT_URL + '?status=already_exists');
    }

    // Criar o filtro
    console.log('✨ Criando filtro para:', senderEmail);

    const filter = await gmail.users.settings.filters.create({
      userId: 'me',
      requestBody: {
        criteria: {
          from: senderEmail
        },
        action: {
          // Marcar com estrela + sempre importante + categoria Principal
          addLabelIds: ['STARRED', 'IMPORTANT', 'CATEGORY_PERSONAL'],
          // Nunca enviar para spam
          neverSpamAction: true
        }
      }
    });

    console.log('✅ Filtro criado com sucesso! ID:', filter.data.id);

    // Redirecionar para página de sucesso
    res.redirect(process.env.SUCCESS_REDIRECT_URL + '?status=created&source=' + state);

  } catch (error) {
    console.error('❌ Erro ao criar filtro:', error.message);

    // Log detalhado para debug
    if (error.response?.data) {
      console.error('Detalhes:', JSON.stringify(error.response.data, null, 2));
    }

    // Determinar tipo de erro para mensagem amigável
    let errorType = 'unknown';
    if (error.message.includes('invalid_grant')) {
      errorType = 'token_expired';
    } else if (error.message.includes('insufficient')) {
      errorType = 'insufficient_permissions';
    }

    res.redirect(process.env.ERROR_REDIRECT_URL + '?error=' + errorType);
  }
});

/**
 * Rota: Status/Health check
 */
app.get('/api/status', (req, res) => {
  res.json({
    status: 'ok',
    sender_email: process.env.SENDER_EMAIL,
    timestamp: new Date().toISOString()
  });
});

// ===========================================
// INICIAR SERVIDOR
// ===========================================

const PORT = process.env.PORT || 3000;

app.listen(PORT, () => {
  console.log('');
  console.log('===========================================');
  console.log('🚀 Gmail Whitelist API rodando!');
  console.log('===========================================');
  console.log('');
  console.log(`📍 URL local: http://localhost:${PORT}`);
  console.log(`📧 Remetente: ${process.env.SENDER_EMAIL}`);
  console.log('');
  console.log('Rotas disponíveis:');
  console.log(`  GET /                    → Página inicial`);
  console.log(`  GET /api/gmail/autorizar → Iniciar OAuth`);
  console.log(`  GET /api/gmail/callback  → Callback do Google`);
  console.log(`  GET /api/status          → Status da API`);
  console.log('');
  console.log('-------------------------------------------');
  console.log('⚠️  Certifique-se de configurar o .env');
  console.log('    com suas credenciais do Google Cloud');
  console.log('-------------------------------------------');
  console.log('');
});
