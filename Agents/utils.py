import os
import yaml
import docker
import time
import logging
from typing import Dict, Any, Optional
from pathlib import Path

logger = logging.getLogger(__name__)


def get_docker_client() -> docker.DockerClient:
    """
    Get Docker client instance.
    
    Returns:
        Docker client
    """
    try:
        client = docker.from_env()
        client.ping()
        return client
    except Exception as e:
        logger.error(f"Failed to connect to Docker: {e}")
        raise


def check_container_health(container_name: str, timeout: int = 60) -> bool:
    """
    Check if a container is healthy and running.
    
    Args:
        container_name: Name of the container
        timeout: Maximum time to wait for health check
        
    Returns:
        True if container is healthy, False otherwise
    """
    client = get_docker_client()
    start_time = time.time()
    
    while time.time() - start_time < timeout:
        try:
            container = client.containers.get(container_name)
            if container.status == 'running':
                # Check health status if available
                health = container.attrs.get('State', {}).get('Health', {})
                if health:
                    if health.get('Status') == 'healthy':
                        return True
                else:
                    # No health check defined, assume healthy if running
                    return True
            time.sleep(2)
        except docker.errors.NotFound:
            logger.warning(f"Container {container_name} not found")
            time.sleep(2)
        except Exception as e:
            logger.error(f"Error checking container health: {e}")
            time.sleep(2)
    
    return False


def get_container_logs(container_name: str, tail: int = 50) -> str:
    """
    Get logs from a container.
    
    Args:
        container_name: Name of the container
        tail: Number of lines to retrieve
        
    Returns:
        Container logs as string
    """
    try:
        client = get_docker_client()
        container = client.containers.get(container_name)
        logs = container.logs(tail=tail).decode('utf-8')
        return logs
    except Exception as e:
        logger.error(f"Failed to get logs for {container_name}: {e}")
        return f"Error: {str(e)}"


def execute_command_in_container(container_name: str, command: str) -> tuple[int, str]:
    """
    Execute a command inside a container.
    
    Args:
        container_name: Name of the container
        command: Command to execute
        
    Returns:
        Tuple of (exit_code, output)
    """
    try:
        client = get_docker_client()
        container = client.containers.get(container_name)
        result = container.exec_run(command)
        return result.exit_code, result.output.decode('utf-8')
    except Exception as e:
        logger.error(f"Failed to execute command in {container_name}: {e}")
        return 1, f"Error: {str(e)}"


def create_docker_compose_file(config: Dict[str, Any], output_path: str = "docker-compose.yml") -> None:
    """
    Create docker-compose.yml file based on configuration.
    
    Args:
        config: Configuration dictionary
        output_path: Path where to save the docker-compose file
    """
    wordpress_config = config['wordpress']
    mysql_config = config['mysql']
    
    compose_content = f"""version: '3.8'

services:
  mysql:
    image: mysql:{mysql_config['version']}
    container_name: wordpress_mysql
    restart: unless-stopped
    environment:
      MYSQL_ROOT_PASSWORD: {mysql_config['database']['root_password']}
      MYSQL_DATABASE: {mysql_config['database']['name']}
      MYSQL_USER: {mysql_config['database']['user']}
      MYSQL_PASSWORD: {mysql_config['database']['password']}
    volumes:
      - mysql_data:/var/lib/mysql
    networks:
      - wordpress_network
    healthcheck:
      test: ["CMD", "mysqladmin", "ping", "-h", "localhost", "-u", "root", "-p{mysql_config['database']['root_password']}"]
      interval: 10s
      timeout: 5s
      retries: 5

  wordpress:
    image: wordpress:{wordpress_config['version']}
    container_name: wordpress_app
    restart: unless-stopped
    depends_on:
      mysql:
        condition: service_healthy
    ports:
      - "{wordpress_config['port']}:80"
    environment:
      WORDPRESS_DB_HOST: mysql:3306
      WORDPRESS_DB_NAME: {mysql_config['database']['name']}
      WORDPRESS_DB_USER: {mysql_config['database']['user']}
      WORDPRESS_DB_PASSWORD: {mysql_config['database']['password']}
    volumes:
      - wordpress_data:/var/www/html
    networks:
      - wordpress_network
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:80/"]
      interval: 10s
      timeout: 5s
      retries: 5

volumes:
  mysql_data:
  wordpress_data:

networks:
  wordpress_network:
    driver: bridge
"""
    
    with open(output_path, 'w') as f:
        f.write(compose_content)
    
    logger.info(f"Docker Compose file created at {output_path}")
