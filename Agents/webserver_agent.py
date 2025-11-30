import logging
import time
import requests
from typing import Dict, Any
from .utils import (
    get_docker_client,
    check_container_health,
    get_container_logs,
    execute_command_in_container
)
from .agent import Agent

logger = logging.getLogger(__name__)


class WebServerAgent(Agent):
    """Agent responsible for web server and PHP configuration."""
    
    def __init__(self, llm, config: Dict[str, Any]):
        """
        Initialize Web Server Agent.
        
        Args:
            llm: LangChain LLM instance
            config: Configuration dictionary
        """
        self.wordpress_config = config['wordpress']
        self.container_name = "wordpress_app"
        self.port = self.wordpress_config['port']
        super().__init__(llm, config, agent_name="WebServerAgent")

    
    def _create_tools(self):
        """Create tools for Web Server agent."""
        
        def check_wordpress_container_status() -> str:
            """Check if WordPress container is running and healthy."""
            try:
                client = get_docker_client()
                container = client.containers.get(self.container_name)
                status = container.status
                health = container.attrs.get('State', {}).get('Health', {}).get('Status', 'N/A')
                return f"Container status: {status}, Health: {health}"
            except Exception as e:
                return f"Error checking container: {str(e)}"
        
        def get_wordpress_logs(lines: int = 50) -> str:
            """
            Get WordPress container logs.
            
            Args:
                lines: Number of log lines to retrieve (default: 50)
            """
            return get_container_logs(self.container_name, tail=lines)
        
        def test_http_response() -> str:
            """Test if WordPress responds to HTTP requests."""
            try:
                url = f"http://localhost:{self.port}"
                response = requests.get(url, timeout=10)
                return f"SUCCESS: HTTP {response.status_code} - WordPress is responding. Content length: {len(response.content)} bytes"
            except requests.exceptions.ConnectionError:
                return "FAILED: Cannot connect to WordPress. Connection refused."
            except requests.exceptions.Timeout:
                return "FAILED: Connection to WordPress timed out."
            except Exception as e:
                return f"FAILED: Error testing WordPress: {str(e)}"
        
        def check_php_version() -> str:
            """Check PHP version installed in WordPress container."""
            command = "php -v"
            exit_code, output = execute_command_in_container(self.container_name, command)
            
            if exit_code == 0:
                return f"SUCCESS: PHP version info:\n{output}"
            else:
                return f"FAILED: Could not get PHP version. Error: {output}"
        
        def check_apache_status() -> str:
            """Check Apache web server status."""
            command = "apache2ctl -t"
            exit_code, output = execute_command_in_container(self.container_name, command)
            
            if exit_code == 0:
                return f"SUCCESS: Apache configuration is valid:\n{output}"
            else:
                return f"WARNING: Apache configuration check:\n{output}"
        
        def verify_wordpress_files() -> str:
            """Verify WordPress files are present."""
            command = "ls -la /var/www/html/ | head -20"
            exit_code, output = execute_command_in_container(self.container_name, command)
            
            if exit_code == 0:
                if "wp-config.php" in output or "wp-admin" in output:
                    return f"SUCCESS: WordPress files are present:\n{output}"
                else:
                    return f"WARNING: WordPress files may be incomplete:\n{output}"
            else:
                return f"FAILED: Could not check WordPress files. Error: {output}"
        
        def check_php_extensions() -> str:
            """Check if required PHP extensions are loaded."""
            command = "php -m"
            exit_code, output = execute_command_in_container(self.container_name, command)
            
            if exit_code == 0:
                required = ['mysqli', 'gd', 'curl', 'zip', 'mbstring']
                loaded = output.lower()
                missing = [ext for ext in required if ext not in loaded]
                
                if not missing:
                    return f"SUCCESS: All required PHP extensions are loaded:\n{output}"
                else:
                    return f"WARNING: Missing extensions: {missing}\nLoaded:\n{output}"
            else:
                return f"FAILED: Could not check PHP extensions. Error: {output}"
        
        def test_wordpress_installation_page() -> str:
            """Test if WordPress installation page is accessible."""
            try:
                url = f"http://localhost:{self.port}/wp-admin/install.php"
                response = requests.get(url, timeout=10, allow_redirects=True)
                
                if response.status_code == 200:
                    if "WordPress" in response.text or "installation" in response.text.lower():
                        return f"SUCCESS: WordPress installation page is accessible and contains expected content."
                    else:
                        return f"WARNING: Page accessible but may not be WordPress installation page. Status: {response.status_code}"
                else:
                    return f"INFO: HTTP {response.status_code} - This is normal if WordPress is already installed."
            except Exception as e:
                return f"ERROR: Could not access installation page: {str(e)}"
        
        def restart_apache() -> str:
            """Restart Apache web server inside the container."""
            command = "apache2ctl graceful"
            exit_code, output = execute_command_in_container(self.container_name, command)
            
            if exit_code == 0:
                return "SUCCESS: Apache restarted successfully."
            else:
                return f"WARNING: Apache restart result: {output}"
        
        def restart_wordpress_container() -> str:
            """Restart the WordPress container."""
            try:
                client = get_docker_client()
                container = client.containers.get(self.container_name)
                container.restart()
                time.sleep(5)
                return "WordPress container restarted successfully."
            except Exception as e:
                return f"Failed to restart WordPress container: {str(e)}"
        
        return self._auto_wrap_tools([
            check_wordpress_container_status,
            get_wordpress_logs,
            test_http_response,
            check_php_version,
            check_apache_status,
            verify_wordpress_files,
            check_php_extensions,
            test_wordpress_installation_page,
            restart_apache,
            restart_wordpress_container
        ])
    
    def _get_system_prompt(self) -> str:
        return """You are a web server administrator agent responsible for ensuring the web server 
            (Apache) and PHP are properly configured for WordPress.
            
            Your responsibilities:
            1. Check if WordPress container is running and healthy
            2. Verify Apache is running correctly
            3. Check PHP version and required extensions
            4. Verify WordPress files are present
            5. Test HTTP connectivity
            6. Test WordPress installation page accessibility
            7. Fix any issues found
            8. Report the final status
            
            Use the available tools to diagnose and fix issues. Always verify your fixes worked.
            Be systematic and thorough. If something fails, analyze the logs and try to fix it.
            
            When you've completed all checks and any necessary fixes, provide a final summary report."""
    
    def validate_and_fix(self) -> Dict[str, Any]:
        """
        Run validation and fix any issues.
        
        Returns:
            Dictionary with status and details
        """
        logger.info("Web Server Agent: Starting validation...")
        
        try:
            # Wait for container to be ready
            logger.info("Waiting for WordPress container to be healthy...")
            if not check_container_health(self.container_name, timeout=60):
                logger.warning("WordPress container health check timed out, proceeding anyway...")
            
            result = self.agent.invoke({
                "input": f"""Perform a complete validation of the web server and PHP setup:
                1. Check container status
                2. Verify Apache is running
                3. Check PHP version and extensions
                4. Verify WordPress files exist
                5. Test HTTP connectivity on port {self.port}
                6. Check WordPress installation page
                7. Fix any issues you find
                8. Confirm everything works after fixes
                
                Provide a final summary of the web server status."""
            })
            
            output = result.get('output', '')
            logger.info(f"Web Server Agent completed: {output}")
            
            return {
                "status": "success",
                "agent": "WebServer",
                "output": output,
                "container": self.container_name
            }
        except Exception as e:
            logger.error(f"Web Server Agent failed: {str(e)}")
            return {
                "status": "error",
                "agent": "WebServer",
                "error": str(e),
                "container": self.container_name
            }
