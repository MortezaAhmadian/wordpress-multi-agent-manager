import logging
import time
from typing import Dict, Any, Optional
from .agent import Agent
from .utils import (
    get_docker_client, 
    check_container_health, 
    get_container_logs,
    execute_command_in_container
)

logger = logging.getLogger(__name__)


class MySQLAgent(Agent):
    """Agent responsible for MySQL database management and validation."""
    
    def __init__(self, llm, config: Dict[str, Any]):
        """
        Initialize MySQL Agent.
        
        Args:
            llm: LangChain LLM instance
            config: Configuration dictionary
        """
        self.mysql_config = config['mysql']
        self.container_name = "wordpress_mysql"
        super().__init__(llm, config, agent_name="MySQLAgent")
        
    
    def _create_tools(self):
        """Create tools for MySQL agent."""
        
        def check_mysql_container_status() -> str:
            """Check if MySQL container is running and healthy."""
            try:
                client = get_docker_client()
                container = client.containers.get(self.container_name)
                status = container.status
                health = container.attrs.get('State', {}).get('Health', {}).get('Status', 'N/A')
                return f"Container status: {status}, Health: {health}"
            except Exception as e:
                return f"Error checking container: {str(e)}"
        
        def get_mysql_logs(lines: int = 50) -> str:
            """
            Get MySQL container logs.
            
            Args:
                lines: Number of log lines to retrieve (default: 50)
            """
            return get_container_logs(self.container_name, tail=lines)
        
        def test_mysql_connection() -> str:
            """Test MySQL database connection and credentials."""
            db_name = self.mysql_config['database']['name']
            db_user = self.mysql_config['database']['user']
            db_pass = self.mysql_config['database']['password']
            
            command = f'mysql -u{db_user} -p{db_pass} -e "SELECT 1;" {db_name}'
            exit_code, output = execute_command_in_container(self.container_name, command)
            
            if exit_code == 0:
                return "SUCCESS: MySQL connection test passed. Database is accessible."
            else:
                return f"FAILED: MySQL connection test failed. Error: {output}"
        
        def verify_database_exists() -> str:
            """Verify that the WordPress database exists."""
            db_name = self.mysql_config['database']['name']
            root_pass = self.mysql_config['database']['root_password']
            
            command = f'mysql -uroot -p{root_pass} -e "SHOW DATABASES LIKE \'{db_name}\';"'
            exit_code, output = execute_command_in_container(self.container_name, command)
            
            if exit_code == 0 and db_name in output:
                return f"SUCCESS: Database '{db_name}' exists."
            else:
                return f"FAILED: Database '{db_name}' not found. Output: {output}"
        
        def verify_user_permissions() -> str:
            """Verify that the WordPress user has proper permissions."""
            db_user = self.mysql_config['database']['user']
            db_name = self.mysql_config['database']['name']
            root_pass = self.mysql_config['database']['root_password']
            
            command = f"mysql -uroot -p{root_pass} -e \"SHOW GRANTS FOR '{db_user}'@'%';\""
            exit_code, output = execute_command_in_container(self.container_name, command)
            
            if exit_code == 0:
                return f"SUCCESS: User permissions retrieved:\n{output}"
            else:
                return f"FAILED: Could not retrieve user permissions. Error: {output}"
        
        def fix_mysql_permissions() -> str:
            """Fix MySQL user permissions if needed."""
            db_user = self.mysql_config['database']['user']
            db_pass = self.mysql_config['database']['password']
            db_name = self.mysql_config['database']['name']
            root_pass = self.mysql_config['database']['root_password']
            
            commands = [
                f"mysql -uroot -p{root_pass} -e \"GRANT ALL PRIVILEGES ON {db_name}.* TO '{db_user}'@'%';\"",
                f"mysql -uroot -p{root_pass} -e \"FLUSH PRIVILEGES;\""
            ]
            
            results = []
            for cmd in commands:
                exit_code, output = execute_command_in_container(self.container_name, cmd)
                results.append(f"Command: {cmd}\nExit Code: {exit_code}\nOutput: {output}")
            
            return "Permissions update attempted:\n" + "\n---\n".join(results)
        
        def restart_mysql_container() -> str:
            """Restart the MySQL container."""
            try:
                client = get_docker_client()
                container = client.containers.get(self.container_name)
                container.restart()
                time.sleep(5)
                return "MySQL container restarted successfully."
            except Exception as e:
                return f"Failed to restart MySQL container: {str(e)}"
        
        return self._auto_wrap_tools([
            check_mysql_container_status,
            get_mysql_logs,
            test_mysql_connection,
            verify_database_exists,
            verify_user_permissions,
            fix_mysql_permissions,
            restart_mysql_container
        ])
    
    
    def _get_system_prompt(self) -> str:
        return """You are a MySQL database administrator agent responsible for ensuring the MySQL database 
        for WordPress is properly configured and running.  

        Your responsibilities:
            1. Check if MySQL container is running and healthy
            2. Verify the WordPress database exists
            3. Test database connectivity with the WordPress credentials
            4. Verify user permissions are correct
            5. Fix any issues found
            6. Report the final status
            
            Use the available tools to diagnose and fix issues. Always verify your fixes worked.
            Be systematic and thorough. If something fails, analyze the logs and try to fix it.
            
            When you've completed all checks and any necessary fixes, provide a final summary report."""                     
    
    
    def validate_and_fix(self) -> Dict[str, Any]:
        """
        Run validation and fix any issues.
        
        Returns:
            Dictionary with status and details
        """
        logger.info("MySQL Agent: Starting validation...")
        
        try:
            # Wait for container to be ready
            logger.info("Waiting for MySQL container to be healthy...")
            if not check_container_health(self.container_name, timeout=60):
                logger.warning("MySQL container health check timed out, proceeding anyway...")
            
            result = self.agent.invoke({
                "input": """Perform a complete validation of the MySQL database setup:
                1. Check container status
                2. Verify database exists
                3. Test database connection
                4. Verify user permissions
                5. Fix any issues you find
                6. Confirm everything works after fixes
                
                Provide a final summary of the database status."""
            })
            
            output = result.get('output', '')
            logger.info(f"MySQL Agent completed: {output}")
            
            return {
                "status": "success",
                "agent": "MySQL",
                "output": output,
                "container": self.container_name
            }
        except Exception as e:
            logger.error(f"MySQL Agent failed: {str(e)}")
            return {
                "status": "error",
                "agent": "MySQL",
                "error": str(e),
                "container": self.container_name
            }
