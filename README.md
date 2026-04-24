<h1 align="center">
<img width="75" src="https://raw.githubusercontent.com/me-oaris/Niro/refs/heads/main/Assets/niro.png" alt="Niro Bot">

niro
</h1>

<p align="center">
The most professional, fully expandable, and self-hostable Discord bot. Designed to provide premium V2 UI components for moderation, leveling, giveaways, and more.
</p>

## Why Niro?

Niro is built with a focus on **Premium UI/UX**. Every interaction is designed using Discord's latest Components V2 system, featuring cool new embed designs, interactive cards, and real-time updates. No more boring embeds!! Niro provides a state-of-the-art experience for your server.

## Features

- **🛡️ Advanced Moderation**: Full suite of tools including Ban, Kick, Mute, Warn, and Lock/Unlock.
- **⚛️ Channel Nuke**: Instantly clone and recreate channels to clear clutter while preserving permissions.
- **⭐ Leveling System**: Interactive rank cards with realtime theme customization (Hex & Presets).
- **🎉 Interactive Giveaways**: Fully managed giveaways with real-time entry counters and winner rerolls.
- **📜 Professional Logging**: Automated logging for message edits, deletions, and moderator actions.
- **⚙️ Dynamic Setup**: Easy-to-use `/setup` menu for configuring welcome messages, roles, and log channels.

## Setup

1. Create a 'New Application' in the [Discord Developer Portal](https://discord.com/developers/applications).
2. Go to the 'Bot' section, enable all 3 **Privileged Gateway Intents** (Presence, Server Members, Message Content).
3. Reset and copy your bot **Token**.
4. Duplicate the `.env.example` (or create a `.env` file) and fill in your `TOKEN` and `GUILD_ID`.
5. Invite the bot to your server using the OAuth2 URL generator with `bot` and `applications.commands` scopes (Administrator permission recommended).
6. Install the required dependencies:
   ```bash
   pip install -r requirements.txt
   ```
7. Run the bot:
   ```bash
   python niro.py
   ```

## Running Locally

Niro is designed to be self-hosted. Once running, use the `/setup` command in your server to initialize your moderation roles and logging preferences. Your leveling data and settings are stored locally in a robust SQLite database (`data/niro.db`).

## License

This project is licensed under the AGPL-3.0.
Additional attribution requirements apply — see the `NOTICE` file for details.
