# 🛡️ RobloxChat by Red65 Studio
RobloxChat is a lightweight, ultra-secure, and private messaging utility designed specifically for developers and gamers. It provides a seamless, encrypted communication layer that can be accessed globally via hotkeys, even while inside other applications.

# ✨ Key Features
* Global Access: Toggle the chat interface instantly using the / key (Numpad or Standard) without Tab-switching.

* End-to-End Encryption (E2EE): Every message is encrypted locally using AES-GCM before it ever leaves your computer.

* Zero-Knowledge Server: The server only handles encrypted payloads. It cannot read your messages, and your room codes are anonymized via SHA-256 hashing.

* Privacy First: No phone numbers or emails required. Access is managed through a UUID-based approval system controlled by the room creator.

* Smart Auto-Updates: Stay up to date with the latest security patches through our built-in seamless update system.

# 🔒 Security & Safety
### Is it safe?
Yes. RobloxChat is 100% Virus-Free.

* Pure Python: The core logic is built using standard, reputable Python libraries such as PyQt5, cryptography, and requests.

* Administrative Rights: The program requests admin privileges only to enable the global hotkey listener and to manage the focus-switching between windows.

* Transparency: While the core repository remains private to protect proprietary encryption "salts" and infrastructure details, the application uses industry-standard encryption protocols (PBKDF2 for key derivation and AES-256-GCM for payloads).

### Why is the source code private?
To ensure the highest level of security for our users, we do not publish the raw client.py or server.py. This prevents malicious actors from analyzing specific cryptographic implementations or attempting to brute-force room identifiers.

# 🚀 How to Use
1. Download: Download the latest .exe from the Releases tab.

2. Run: Launch the application (Admin rights recommended for the hotkey to work inside games).

3. Setup: Enter your display name.

4. Connect: Create a new room to get a 6-character hex code, or enter a code provided by a friend.

5. Chat: Press / or on the input field at any time to focus the input field and start typing.

# 🛠️ Requirements
* Windows 10/11

* Internet Connection

* Windowed or Borderless Window mode (for best results when using the overlay in-game).


> [!NOTE]
> RobloxChat is an independent project by Red65 Studio and is not affiliated with, authorized, maintained, sponsored, or endorsed by Roblox Corporation.
