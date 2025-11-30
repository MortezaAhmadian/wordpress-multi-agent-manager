# WordPress Multi-Agent Manager

An intelligent WordPress installation and management system powered by LangChain and AI agents. This system uses multiple specialized AI agents to orchestrate, deploy, validate, and maintain WordPress installations through Docker Compose.

## 🌟 Features

- **Multi-Agent Architecture**: Specialized agents for different components:
  - **Orchestrator Agent**: Manages the overall installation workflow
  - **MySQL Agent**: Handles database setup, validation, and fixes
  - **Web Server Agent**: Manages Apache/PHP configuration and validation
  
- **Intelligent Self-Healing**: Agents can detect and automatically fix common issues
- **Flexible Configuration**: Easy YAML-based configuration for all settings
- **LLM-Powered Decisions**: Uses large language models to make intelligent decisions about setup and troubleshooting
- **Docker-Based**: Clean, isolated WordPress installations using Docker Compose
- **Multiple LLM Providers**: Supports Anthropic Claude, OpenAI, and other providers

## 📋 Prerequisites

- **Operating System**: Unix-based OS (Linux, macOS)
- **Docker**: Version 20.10 or higher
- **Docker Compose**: Version 2.0 or higher
- **Python**: Version 3.8 or higher
- **API Key**: For your chosen LLM provider (Anthropic, OpenAI, etc.)

### Installing Docker (if needed)

**Ubuntu/Debian:**
```bash
sudo apt-get update
sudo apt-get install docker.io docker-compose
sudo systemctl start docker
sudo usermod -aG docker $USER
```

**macOS:**
```bash
brew install docker docker-compose
```

## 🚀 Installation

1. **Clone or download the project files**

2. **Install Python dependencies:**
```bash
pip install -r requirements.txt
```

Or with system packages flag:
```bash
pip install -r requirements.txt --break-system-packages
```

3. **Set up your API key:**

Create a `.env` file in the project directory:
```bash
echo "ANTHROPIC_API_KEY=your_api_key_here" > .env
```

Or export it directly:
```bash
export ANTHROPIC_API_KEY=your_api_key_here
```

4. **Review and customize the configuration:**

Edit `config.yaml` to customize your WordPress installation settings.

## ⚙️ Configuration

The `config.yaml` file contains all configuration options:

### LLM Configuration
```yaml
llm:
  provider: "anthropic"  # or "openai"
  model: "claude-sonnet-4-20250514"
  api_key: "${ANTHROPIC_API_KEY}"
  temperature: 0.1
  max_tokens: 4096
```

### WordPress Configuration
```yaml
wordpress:
  version: "latest"
  port: 8083
  admin:
    user: "admin"
    password: "admin_password_123"
    email: "admin@example.com"
```

### MySQL Configuration
```yaml
mysql:
  version: "8.0"
  port: 3306
  database:
    name: "wordpress_db"
    user: "wordpress_user"
    password: "wordpress_password_123"
    root_password: "root_password_123"
```

### Agent Configuration
```yaml
agents:
  max_iterations: 5
  verbose: true
  auto_fix: true  # Enable automatic issue fixing
```

## 🎯 Usage

### Basic Commands

**Install WordPress:**
```bash
python main.py install
```

**Update existing installation:**
```bash
python main.py update
```

**Validate current installation:**
```bash
python main.py validate
```

**Use custom configuration file:**
```bash
python main.py install --config my-config.yaml
```

**Enable verbose output:**
```bash
python main.py install --verbose
```

### What Happens During Installation

1. **Orchestrator Agent** starts and checks prerequisites
2. Creates or validates `docker-compose.yml`
3. Starts MySQL and WordPress containers
4. **MySQL Agent** validates:
   - Container health
   - Database creation
   - User permissions
   - Connectivity
5. **Web Server Agent** validates:
   - Apache configuration
   - PHP version and extensions
   - WordPress files
   - HTTP connectivity
6. Agents automatically fix any issues found
7. Provides final summary with access URL

## 🔍 Architecture

```
┌─────────────────────────────────────────┐
│      Orchestrator Agent (Main)          │
│  - Workflow coordination                │
│  - Docker Compose management            │
│  - Agent delegation                     │
└─────────────┬───────────────────────────┘
              │
    ┌─────────┴─────────┐
    │                   │
┌───▼────────┐   ┌──────▼──────┐
│   MySQL    │   │  Web Server │
│   Agent    │   │    Agent    │
│            │   │             │
│ - Database │   │ - Apache    │
│ - Users    │   │ - PHP       │
│ - Perms    │   │ - WordPress │
└────────────┘   └─────────────┘
```

### Agent Tools

Each agent has specialized tools:

**MySQL Agent Tools:**
- `check_mysql_container_status()` - Check container health
- `test_mysql_connection()` - Test database connectivity
- `verify_database_exists()` - Verify database creation
- `verify_user_permissions()` - Check user permissions
- `fix_mysql_permissions()` - Repair permissions
- `get_mysql_logs()` - Retrieve container logs

**Web Server Agent Tools:**
- `check_wordpress_container_status()` - Check container health
- `test_http_response()` - Test HTTP connectivity
- `check_php_version()` - Verify PHP installation
- `check_php_extensions()` - Check required extensions
- `verify_wordpress_files()` - Validate WordPress files
- `check_apache_status()` - Verify Apache configuration

**Orchestrator Agent Tools:**
- `check_docker_running()` - Verify Docker daemon
- `create_compose_file()` - Generate docker-compose.yml
- `docker_compose_up()` - Start containers
- `validate_mysql_setup()` - Run MySQL agent
- `validate_webserver_setup()` - Run Web Server agent

## 🔧 Troubleshooting

### Docker Permission Issues
```bash
sudo usermod -aG docker $USER
# Log out and log back in
```

### Port Already in Use
Edit `config.yaml` and change the WordPress port:
```yaml
wordpress:
  port: 8081  # or another available port
```

### API Key Issues
Ensure your API key is correctly set:
```bash
echo $ANTHROPIC_API_KEY  # Should display your key
```

### Container Issues
View logs:
```bash
docker logs wordpress_mysql
docker logs wordpress_app
```

Reset everything:
```bash
docker-compose down -v
python main.py install
```

## 🎓 Examples

### Example 1: Basic Installation
```bash
# Install with default settings
python main.py install

# Access WordPress
# Open browser: http://localhost:8080
```

### Example 2: Custom Configuration
```bash
# Create custom config
cp config.yaml production.yaml

# Edit production.yaml with your settings

# Install with custom config
python main.py install --config production.yaml
```

### Example 3: Validation Only
```bash
# Validate existing installation
python main.py validate

# Agents will check all components and report status
```

### Example 4: Update Installation
```bash
# Modify config.yaml (e.g., change WordPress version)

# Run update
python main.py update

# Agents will update containers and re-validate
```

## 🔒 Security Considerations

1. **Change Default Passwords**: Always update passwords in `config.yaml`
2. **API Keys**: Never commit API keys to version control
3. **Production Use**: This is a development tool; harden for production
4. **Firewall**: Limit Docker port exposure in production environments

## 🤝 How It Works

### Agent Decision Making

The system leverages LLMs to make intelligent decisions at each step:

1. **Analysis**: Each agent analyzes the current state using its tools
2. **Planning**: The LLM determines what actions to take
3. **Execution**: Tools are called to perform actions
4. **Validation**: Results are checked and validated
5. **Self-Healing**: If issues are found, agents attempt fixes
6. **Reporting**: Final status is reported to the orchestrator

### LLM Integration

- Agents use LangChain's tool-calling capabilities
- Each tool provides clear output for the LLM to interpret
- The LLM decides which tools to call and in what order
- System prompts guide agents to be thorough and systematic
- Agents can iterate and retry with different approaches

## 📊 Logging

Logs are written to `wordpress_manager.log` by default. Configure in `config.yaml`:

```yaml
logging:
  level: "INFO"  # DEBUG, INFO, WARNING, ERROR
  file: "wordpress_manager.log"
  format: "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
```

## 🌐 Accessing WordPress

After successful installation:

1. Open your browser to `http://localhost:8080` (or your configured port)
2. Complete the WordPress installation wizard
3. Use the admin credentials from `config.yaml`

## 🚧 Limitations

- Requires Docker and Docker Compose pre-installed
- Currently supports MySQL 8.0 and WordPress latest
- Designed for development/testing environments
- Agent iterations are limited (configurable)

## 📝 License

This project is provided as-is for educational and development purposes.

## 🙏 Acknowledgments

- Built with [LangChain](https://github.com/langchain-ai/langchain)
- Uses [Docker](https://www.docker.com/) for containerization
- Powered by AI models from Anthropic, OpenAI, and others

## 📧 Support

For issues or questions, please check the logs in `wordpress_manager.log` for detailed error messages.

---

**Happy WordPress Managing! 🚀**
