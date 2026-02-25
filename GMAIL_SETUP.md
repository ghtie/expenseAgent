# Gmail Integration Setup

This guide walks you through connecting the expense agent to a dedicated Gmail account so it can automatically read transaction emails.

## Part 1: Auto-Forward Emails to Your Expense Gmail

You'll set up your **primary Gmail** to automatically forward Capital One and Venmo emails to your **expense Gmail**.

### Add a forwarding address

1. In your **primary Gmail**, go to **Settings** (gear icon) > **See all settings** > **Forwarding and POP/IMAP**
2. Click **Add a forwarding address**
3. Enter your expense Gmail address and click **Next**
4. Sign into your expense Gmail and click the confirmation link

### Create a filter to auto-forward

1. In your **primary Gmail**, click the search bar dropdown (filter icon)
2. In the **From** field, enter:
   ```
   alerts@notify.capitalone.com OR venmo@venmo.com
   ```
3. Click **Create filter**
4. Check **Forward it to** and select your expense Gmail address
5. Optionally check **Skip the Inbox** to keep your primary inbox clean
6. Click **Create filter**

New transaction emails will now be auto-forwarded to your expense Gmail.

## Part 2: Google Cloud Project Setup

You need a Google Cloud project with the Gmail API enabled so the agent can authenticate.

### Create a project

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Click the project dropdown at the top > **New Project**
3. Name it something like `expense-agent` and click **Create**

### Enable the Gmail API

1. Go to **APIs & Services** > **Library**
2. Search for **Gmail API** and click on it
3. Click **Enable**

### Create the OAuth consent screen

1. Go to **APIs & Services** > **OAuth consent screen**
2. Select **External** and click **Create**
3. Fill in the required fields:
   - **App name**: `Expense Agent`
   - **User support email**: your email
   - **Developer contact**: your email
4. Click **Save and Continue** through the remaining steps
5. On the **Test users** screen, click **Add Users** and enter your **expense Gmail address**
6. Click **Save and Continue**

### Create OAuth credentials

1. Go to **APIs & Services** > **Credentials**
2. Click **Create Credentials** > **OAuth client ID**
3. Select **Desktop app** as the application type
4. Name it `Expense Agent Desktop`
5. Click **Create**
6. Click **Download JSON** and save the file as `credentials.json` in the project root (same folder as `main.py`)

## Part 3: First Run

1. Install the new dependencies:
   ```bash
   pip install -r requirements.txt
   ```

2. Make sure `credentials.json` is in the project root.

3. Run the agent in Gmail mode:
   ```bash
   python main.py --gmail
   ```

4. A browser window will open. Sign in with your **expense Gmail account** and grant the requested permission (read and modify emails).

5. The agent will save a `token.json` file for future runs — you won't need to authenticate again unless the token expires.

6. The agent will fetch all unread emails, process each one, and mark successfully processed emails as read.

### Subsequent runs

Just run `python main.py --gmail` again. It will only process new unread emails.
