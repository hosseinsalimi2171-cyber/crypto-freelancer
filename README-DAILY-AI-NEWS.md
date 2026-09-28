# Daily AI Technology News

CryptoEngineer can automatically refresh its Technology & AI news desk once per day using OpenAI and public RSS feeds.

## What it does

- Collects recent stories from the configured technology publications.
- Sends the candidate headlines/metadata to OpenAI GPT-5.6 Luna for editorial selection and original short summaries.
- Resolves article images from RSS media or the article's `og:image` metadata.
- Rewrites `news-feed.js` with the selected stories.
- Commits the update back to `main` through GitHub Actions.
- Cloudflare Pages then redeploys the updated static site automatically.

## One-time security setup

Do **not** put an OpenAI API key into HTML, JavaScript, `config.js`, or any public file.

In GitHub:

1. Open the `crypto-freelancer` repository.
2. Go to **Settings → Secrets and variables → Actions**.
3. Click **New repository secret**.
4. Name it exactly `OPENAI_API_KEY`.
5. Paste your OpenAI API key into the Secret field.
6. Click **Add secret**.

The workflow reads the key only from the GitHub Actions secret.

## Manual test

After the workflow is pushed, open **GitHub → Actions → Daily AI Technology News → Run workflow** to test it immediately. The normal schedule runs once per day.
