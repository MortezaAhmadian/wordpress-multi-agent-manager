import logging
import subprocess
import os
from typing import Dict, Any
from pathlib import Path
from .utils import (
    get_docker_client,
    create_docker_compose_file,
    check_container_health
)
from .agent import Agent
from .mysql_agent import MySQLAgent
from .webserver_agent import WebServerAgent

logger = logging.getLogger(__name__)


class OrchestratorAgent(Agent):
    """Main orchestrator agent that manages the entire WordPress installation."""
    
    def __init__(self, llm, config: Dict[str, Any]):
        """
        Initialize Orchestrator Agent.
        
        Args:
            llm: LangChain LLM instance
            config: Configuration dictionary
        """   
        self.docker_config = config['docker']
        self.compose_file = self.docker_config['compose_file']
        self.project_name = self.docker_config['project_name']
        self.mysql_agent = None
        self.webserver_agent = None
        super().__init__(llm, config, agent_name="OrchestratorAgent")
        
    
    def _create_tools(self):
        """Create tools for Orchestrator agent."""
        
        def check_docker_compose_file_exists() -> str:
            """Check if docker-compose.yml file exists."""
            if Path(self.compose_file).exists():
                return f"SUCCESS: {self.compose_file} exists."
            else:
                return f"NOT FOUND: {self.compose_file} does not exist. Need to create it."
        
        def create_compose_file() -> str:
            """Create docker-compose.yml file based on configuration."""
            try:
                create_docker_compose_file(self.config, self.compose_file)
                return f"SUCCESS: Created {self.compose_file}"
            except Exception as e:
                return f"FAILED: Could not create docker-compose file: {str(e)}"
        
        def check_docker_running() -> str:
            """Check if Docker daemon is running."""
            try:
                client = get_docker_client()
                info = client.info()
                return f"SUCCESS: Docker is running. Version: {info.get('ServerVersion', 'unknown')}"
            except Exception as e:
                return f"FAILED: Docker is not running or not accessible: {str(e)}"
        
        def check_existing_containers() -> str:
            """Check if WordPress containers already exist."""
            try:
                client = get_docker_client()
                containers = client.containers.list(all=True, filters={"name": "wordpress"})
                
                if containers:
                    status_info = []
                    for container in containers:
                        status_info.append(f"- {container.name}: {container.status}")
                    return f"FOUND: Existing WordPress containers:\n" + "\n".join(status_info)
                else:
                    return "NOT FOUND: No existing WordPress containers."
            except Exception as e:
                return f"ERROR: Could not check containers: {str(e)}"
        
        def docker_compose_up() -> str:
            """Start WordPress stack using docker-compose."""
            try:
                cmd = ["docker-compose", "-f", self.compose_file, "-p", self.project_name, "up", "-d"]
                result = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
                
                if result.returncode == 0:
                    return f"SUCCESS: Docker Compose started.\nOutput: {result.stdout}"
                else:
                    return f"FAILED: Docker Compose failed.\nError: {result.stderr}\nOutput: {result.stdout}"
            except subprocess.TimeoutExpired:
                return "FAILED: Docker Compose command timed out after 120 seconds."
            except Exception as e:
                return f"FAILED: Could not run docker-compose: {str(e)}"
        
        def docker_compose_down() -> str:
            """Stop WordPress stack using docker-compose."""
            try:
                cmd = ["docker-compose", "-f", self.compose_file, "-p", self.project_name, "down"]
                result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
                
                if result.returncode == 0:
                    return f"SUCCESS: Docker Compose stopped.\nOutput: {result.stdout}"
                else:
                    return f"WARNING: Docker Compose down had issues.\nError: {result.stderr}"
            except Exception as e:
                return f"ERROR: Could not stop docker-compose: {str(e)}"
        
        def docker_compose_restart() -> str:
            """Restart WordPress stack using docker-compose."""
            try:
                # Stop first
                subprocess.run(
                    ["docker-compose", "-f", self.compose_file, "-p", self.project_name, "down"],
                    capture_output=True, text=True, timeout=60
                )
                
                # Start again
                result = subprocess.run(
                    ["docker-compose", "-f", self.compose_file, "-p", self.project_name, "up", "-d"],
                    capture_output=True, text=True, timeout=120
                )
                
                if result.returncode == 0:
                    return f"SUCCESS: Docker Compose restarted.\nOutput: {result.stdout}"
                else:
                    return f"FAILED: Docker Compose restart failed.\nError: {result.stderr}"
            except Exception as e:
                return f"FAILED: Could not restart docker-compose: {str(e)}"
        
        def validate_mysql_setup() -> str:
            """Run MySQL agent to validate database setup."""
            try:
                if not self.mysql_agent:
                    logger.info("Creating MySQL Agent for validation...")
                    self.mysql_agent = MySQLAgent(self.llm, self.config)
                    logger.info("MySQL Agent created successfully")
                
                logger.info("Running MySQL Agent validation...")
                result = self.mysql_agent.validate_and_fix()
                logger.info(f"MySQL Agent validation completed: {result['status']}")
                
                if result['status'] == 'success':
                    return f"SUCCESS: MySQL validation completed.\n{result['output']}"
                else:
                    return f"FAILED: MySQL validation failed.\n{result.get('error', 'Unknown error')}"
            except Exception as e:
                return f"ERROR: Could not run MySQL agent: {str(e)}"
        
        def validate_webserver_setup() -> str:
            """Run Web Server agent to validate Apache/PHP setup."""
            try:
                if not self.webserver_agent:
                    logger.info("Creating Web Server Agent for validation...")
                    self.webserver_agent = WebServerAgent(self.llm, self.config)
                    logger.info("Web Server Agent created successfully")
                
                logger.info("Running Web Server Agent validation...")
                result = self.webserver_agent.validate_and_fix()
                logger.info(f"Web Server Agent validation completed: {result['status']}")
                
                if result['status'] == 'success':
                    return f"SUCCESS: Web Server validation completed.\n{result['output']}"
                else:
                    return f"FAILED: Web Server validation failed.\n{result.get('error', 'Unknown error')}"
            except Exception as e:
                return f"ERROR: Could not run Web Server agent: {str(e)}"
        
        def get_wordpress_url() -> str:
            """Get the URL where WordPress is accessible."""
            port = self.config['wordpress']['port']
            return f"WordPress should be accessible at: http://localhost:{port}"
        
        def get_installation_summary() -> str:
            """Get a summary of the installation configuration."""
            wp = self.config['wordpress']
            mysql = self.config['mysql']
            
            summary = f"""
                        WordPress Installation Summary:
                        ================================
                        WordPress URL: http://localhost:{wp['port']}
                        WordPress Version: {wp['version']}

                        Database Configuration:
                        - Database Name: {mysql['database']['name']}
                        - Database User: {mysql['database']['user']}
                        - MySQL Version: {mysql['version']}

                        Admin Credentials (for WordPress setup):
                        - Username: {wp['admin']['user']}
                        - Email: {wp['admin']['email']}
                        - Password: {wp['admin']['password']}

                        Docker Configuration:
                        - Project Name: {self.docker_config['project_name']}
                        - Compose File: {self.compose_file}
                        """
            return summary
        
        return self._auto_wrap_tools([
            check_docker_compose_file_exists,
            create_compose_file,
            check_docker_running,
            check_existing_containers,
            docker_compose_up,
            docker_compose_down,
            docker_compose_restart,
            validate_mysql_setup,
            validate_webserver_setup,
            get_wordpress_url,
            get_installation_summary
        ])
    
    def _get_system_prompt(self) -> str:
        return """You are the main orchestrator agent responsible for managing the complete 
            WordPress installation using Docker Compose.
            
            Your responsibilities:
            1. Check if Docker is running
            2. Check for existing WordPress installations
            3. Create or update docker-compose.yml if needed
            4. Start the WordPress stack with docker-compose
            5. Delegate to MySQL agent for database validation (MANDATORY)
            6. Delegate to Web Server agent for Apache/PHP validation (MANDATORY)
            7. Ensure all components are working together
            8. Provide final installation summary with access URLs
            
            WORKFLOW:
            - First check if docker-compose.yml exists, create if needed
            - Check Docker is running
            - Check for existing containers (decide whether to restart or start fresh)
            - Start containers with docker-compose up
            - Wait a bit for containers to initialize
            - MANDATORY - Call validate_mysql_setup tool
            - MANDATORY - Call validate_webserver_setup tool
            - If any validation fails and auto-fix is enabled, try to fix and re-validate
            - Provide final summary
            
            IMPORTANT: You MUST call validate_mysql_setup and validate_webserver_setup tools.
            These tools will wait for containers to be ready, then validate everything.
            Do NOT skip validation steps - they are required for a complete installation.
            
            Use the available tools systematically. Be thorough and handle errors gracefully.
            When delegating to sub-agents, trust their expertise and report their findings.
            
            When everything is complete, provide a comprehensive summary with access instructions."""

    
    def run(self, command: str = "install") -> Dict[str, Any]:
        """
        Run the orchestrator agent.
        
        Args:
            command: Command to execute (install, update, or validate)
            
        Returns:
            Dictionary with execution results
        """
        logger.info(f"Orchestrator Agent: Starting '{command}' operation...")
        
        command_prompts = {
            "install": """Install and configure WordPress - Follow ALL steps:
                1. Check if docker-compose.yml exists, create if needed
                2. Check Docker is running
                3. Check for existing containers
                4. Start WordPress stack with docker-compose
                5. CALL validate_mysql_setup tool (REQUIRED)
                6. CALL validate_webserver_setup tool (REQUIRED)
                7. CALL get_installation_summary tool
                8. Provide final summary with access URL
                
                CRITICAL: Steps 5, 6, and 7 are MANDATORY. You must call these tools.""",
            
            "update": """Update existing WordPress installation:
                1. Check current installation status
                2. Stop existing containers
                3. Update docker-compose.yml with new configuration
                4. Start containers with updated configuration
                5. Validate all components
                6. Provide update summary""",
            
            "validate": """Validate existing WordPress installation:
                1. Check if containers are running
                2. Validate MySQL setup using the MySQL agent
                3. Validate Web Server setup using the Web Server agent
                4. Provide validation report"""
        }
        
        prompt = command_prompts.get(command, command_prompts["install"])
        
        try:
            result = self.agent.invoke({"input": prompt})
            output = result.get('output', '')
            logger.info(f"Orchestrator Agent completed successfully")
            
            return {
                "status": "success",
                "command": command,
                "output": output
            }
        except Exception as e:
            logger.error(f"Orchestrator Agent failed: {str(e)}")
            return {
                "status": "error",
                "command": command,
                "error": str(e)
            }
