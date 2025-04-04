# ChatGPT Clone Documentation

## Project Overview

The ChatGPT Clone is a Flask-based web application that allows users to interact with AI models through a chat interface. This project integrates user authentication, registration key management, and conversation storage in a relational database.

## Table of Contents

1. [Installation](#installation)
2. [Project Structure](#project-structure)
3. [Configuration](#configuration)
4. [Database](#database)
5. [Routes](#routes)
6. [Models](#models)
7. [Frontend](#frontend)
8. [Testing](#testing)
9. [Usage](#usage)

## Installation

1. Clone the repository:

   ```bash
   git clone <repository-url>
   cd <repository-directory>
   ```

2. Create a `virtualenv` and activate it:

   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows use `venv\Scripts\activate`
   ```

3. Install the required dependencies:

   ```bash
   pip install -r requirements.txt
   ```

4. Create an `.env` file based on the provided `.env.example` and fill in your credentials for OpenAI and other services.

5. Run the setup script to initialize the database:

   ```bash
   python setup.py
   ```

## Project Structure

```
teamgpt/
├── .env
├── .git/
├── .gitignore
├── __pycache__/
├── app/
│   ├── __init__.py
│   ├── config/
│   ├── models/
│   ├── routes/
│   ├── services/
│   ├── static/
│   ├── templates/
│   ├── tools/
│   └── utils/
├── instance/
│   └── chatgpt_clone.db
├── keys.txt
├── load_client.py
├── migrations/
├── requirements.txt
├── run.py
└── setup.py
```

## Configuration

- The application uses Flask configuration classes for different environments (`DevelopmentConfig`, `TestingConfig`, `ProductionConfig`).
- Environment variables are loaded from a `.env` file using Python's `dotenv` library.

## Database

- The application uses SQLite for persistent storage of user accounts, conversations, messages, and registration keys.
- Database initialization is handled in `setup.py`, where tables are created as needed.

### Tables

- `users`: Contains user credentials and timestamps.
- `conversations`: Stores conversation metadata.
- `messages`: Stores each message within conversations.
- `registration_keys`: Tracks registration keys and their usage.

## Routes

### Authentication Routes

- `GET /login`: Display the login page.
- `GET /register`: Display the registration page.
- `POST /api/register`: User registration endpoint.
- `POST /api/login`: User login endpoint.
- `POST /api/refresh`: Refresh token endpoint.
- `GET /api/me`: Get current user information.

### Chat Routes

- `GET /conversations`: List all conversations for logged-in users.
- `POST /conversations`: Create a new conversation.
- `GET /conversations/<id>`: Retrieve a conversation by ID.
- `DELETE /conversations/<id>`: Delete a conversation.
- `POST /conversations/<id>/messages`: Send a message to a conversation.
- `POST /conversations/<id>/stream`: Stream messages.

### Admin Routes

- `GET /admin/keys`: Admin page for managing registration keys.
- `POST /api/admin/keys/generate`: Generate new registration key.
- `POST /api/admin/keys/load`: Load registration keys from a file.

## Models

### User Model

- Handles user-related operations including creation, retrieval, and password verification.

### Conversation Model

- Manages conversation creation and retrieval.

### Message Model

- Manages message creation and retrieval within conversations.

### Registration Key Model

- Handles registration key creation, validation, and status management.

## Frontend

- Uses HTML5, CSS3, and JavaScript for user interaction.
- Static assets are stored in the `static` folder while dynamic content is rendered through Jinja templates in the `templates` folder.

### Key Interfaces

- **Login:** Input fields for username and password.
- **Register:** Input fields for username, password, confirmation, and registration key.
- **Chat Interface:** Contains a chat history window and input area for user messages.

## Testing

- Use `pytest` for automated testing capabilities.
- Test cases are designed to validate functionality such as user authentication, message handling, and registration key workflows.

## Usage

1. Start the Flask development server:

   ```bash
   python run.py
   ```

2. Visit `http://localhost:5000` in your web browser.

3. Use the application to register, log in, and interact with AI models through chat.

## Credits

- Built using Flask, SQLite, and various Python libraries.
- Leveraging the OpenAI API for conversation generation.