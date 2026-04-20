# Gmail Whitelist App

Aplicativo para criar filtros automaticamente no Gmail dos seus leads via OAuth 2.0.

## O que faz

Quando o usuário clica no botão e autoriza, o app cria um filtro no Gmail dele que:
- ✅ Marca seus emails como **importantes**
- ✅ Garante que nunca vão para **spam**

## Pré-requisitos

- Node.js 18+
- Conta no Google Cloud Console

---

## Configuração do Google Cloud (Passo a Passo)

### 1. Criar projeto no Google Cloud

1. Acesse [console.cloud.google.com](https://console.cloud.google.com)
2. Clique em **Selecionar projeto** → **Novo projeto**
3. Nome: "Gmail Whitelist" (ou outro de sua preferência)
4. Clique em **Criar**

### 2. Ativar a Gmail API

1. No menu lateral, vá em **APIs e Serviços** → **Biblioteca**
2. Busque por "Gmail API"
3. Clique em **Gmail API** → **Ativar**

### 3. Configurar tela de consentimento OAuth

1. Vá em **APIs e Serviços** → **Tela de consentimento OAuth**
2. Selecione **Externo** → **Criar**
3. Preencha:
   - **Nome do app**: Nome que aparecerá para o usuário
   - **Email de suporte**: Seu email
   - **Logo** (opcional): Sua logo
4. Clique em **Salvar e continuar**
5. Na tela de **Escopos**, clique em **Adicionar ou remover escopos**
6. Busque e marque: `https://www.googleapis.com/auth/gmail.settings.basic`
7. Clique em **Atualizar** → **Salvar e continuar**
8. Na tela de **Usuários de teste**, adicione os emails para teste
9. Clique em **Salvar e continuar**

### 4. Criar credenciais OAuth

1. Vá em **APIs e Serviços** → **Credenciais**
2. Clique em **Criar credenciais** → **ID do cliente OAuth**
3. Tipo: **Aplicativo da Web**
4. Nome: "Gmail Whitelist Web"
5. Em **URIs de redirecionamento autorizados**, adicione:
   - `http://localhost:3000/api/gmail/callback` (para desenvolvimento)
   - `https://seudominio.com/api/gmail/callback` (para produção)
6. Clique em **Criar**
7. **Copie o Client ID e Client Secret** - você vai precisar!

---

## Instalação

### 1. Clone/baixe o projeto

```bash
cd gmail-whitelist-app
```

### 2. Instale as dependências

```bash
cd backend
npm install
```

### 3. Configure as variáveis de ambiente

```bash
# Copie o arquivo de exemplo
cp .env.example .env

# Edite o .env com suas credenciais
nano .env
```

Preencha:
```env
GOOGLE_CLIENT_ID=seu_client_id.apps.googleusercontent.com
GOOGLE_CLIENT_SECRET=seu_client_secret
BASE_URL=http://localhost:3000
PORT=3000
SENDER_EMAIL=contato@seudominio.com
SUCCESS_REDIRECT_URL=http://localhost:3000/sucesso.html
ERROR_REDIRECT_URL=http://localhost:3000/erro.html
```

### 4. Inicie o servidor

```bash
npm start
```

### 5. Teste

Acesse `http://localhost:3000` e clique em "Autorizar com Google"

---

## Deploy em Produção

### Opção 1: Heroku

```bash
# Login no Heroku
heroku login

# Criar app
heroku create gmail-whitelist-app

# Configurar variáveis
heroku config:set GOOGLE_CLIENT_ID=xxx
heroku config:set GOOGLE_CLIENT_SECRET=xxx
heroku config:set BASE_URL=https://seu-app.herokuapp.com
heroku config:set SENDER_EMAIL=contato@seudominio.com
heroku config:set SUCCESS_REDIRECT_URL=https://seu-app.herokuapp.com/sucesso.html
heroku config:set ERROR_REDIRECT_URL=https://seu-app.herokuapp.com/erro.html

# Deploy
git push heroku main
```

### Opção 2: Railway/Render/Vercel

Siga a documentação de cada plataforma, configurando as variáveis de ambiente.

### Opção 3: VPS próprio

```bash
# Instalar PM2
npm install -g pm2

# Iniciar com PM2
pm2 start backend/server.js --name gmail-whitelist

# Configurar inicialização automática
pm2 startup
pm2 save
```

---

## Importante: Verificação do Google

⚠️ **Modo de teste**: Inicialmente seu app só funciona para emails que você adicionar como "Usuários de teste" no Google Cloud Console.

**Para publicar para qualquer usuário**, você precisa passar pela verificação do Google:

1. No Google Cloud Console, vá em **Tela de consentimento OAuth**
2. Clique em **Publicar app**
3. Você precisará fornecer:
   - Política de privacidade (URL)
   - Termos de uso (URL)
   - Vídeo demonstrando o uso do app
   - Justificativa de por que precisa do escopo
   - Domínio verificado

O processo pode levar de 2 a 6 semanas.

---

## Como usar na sua página

### Opção 1: Link direto

```html
<a href="https://seu-app.com/api/gmail/autorizar">
  Garantir entrega dos emails
</a>
```

### Opção 2: Botão estilizado

```html
<a href="https://seu-app.com/api/gmail/autorizar"
   style="background: #4285f4; color: white; padding: 15px 30px; border-radius: 8px; text-decoration: none;">
  Garantir que os emails cheguem
</a>
```

### Opção 3: Na thank you page

Adicione o botão na sua página de obrigado após captura de lead.

### Opção 4: Pop-up após opt-in

```javascript
// Após o lead se cadastrar
setTimeout(() => {
  window.open('https://seu-app.com/api/gmail/autorizar', 'gmail-whitelist', 'width=500,height=600');
}, 2000);
```

---

## Customização

### Mudar cores/estilo

Edite os arquivos em `/frontend/`:
- `index.html` - Página inicial
- `sucesso.html` - Página de sucesso
- `erro.html` - Página de erro

### Adicionar tracking

No `server.js`, você pode adicionar eventos para seu analytics:

```javascript
// Após criar filtro com sucesso
console.log('Filtro criado para:', userEmail);
// Enviar para seu sistema de analytics/CRM
```

---

## Suporte

Se tiver dúvidas sobre a configuração, verifique:
1. As credenciais no `.env` estão corretas
2. A URL de callback está cadastrada no Google Cloud
3. O email está na lista de usuários de teste (durante desenvolvimento)

---

## Licença

MIT - Use como quiser!
