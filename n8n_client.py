import aiohttp
import logging
from typing import Dict, List, Optional, Any

logger = logging.getLogger(__name__)

class N8NClient:
    """Клиент для работы с n8n API"""
    
    def __init__(self, base_url: str, api_key: str):
        self.base_url = base_url.rstrip('/')
        self.api_key = api_key
        self.headers = {
            'X-N8N-API-KEY': api_key,
            'Content-Type': 'application/json'
        }
    
    async def _make_request(self, method: str, endpoint: str, data: Optional[Dict] = None) -> Dict:
        """Выполнение HTTP запроса к n8n API"""
        url = f"{self.base_url}/api/v1/{endpoint.lstrip('/')}"
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.request(
                    method=method,
                    url=url,
                    headers=self.headers,
                    json=data,
                    timeout=aiohttp.ClientTimeout(total=30)
                ) as response:
                    if response.status == 200:
                        return await response.json()
                    else:
                        logger.error(f"n8n API error: {response.status} - {await response.text()}")
                        return {"error": f"HTTP {response.status}"}
        except Exception as e:
            logger.error(f"n8n API request failed: {str(e)}")
            return {"error": str(e)}
    
    async def get_workflows(self) -> List[Dict]:
        """Получение списка всех рабочих процессов"""
        result = await self._make_request('GET', 'workflows')
        if 'error' in result:
            return []
        return result.get('data', [])
    
    async def get_workflow_status(self, workflow_id: str) -> Dict:
        """Получение статуса рабочего процесса"""
        return await self._make_request('GET', f'workflows/{workflow_id}')
    
    async def activate_workflow(self, workflow_id: str) -> Dict:
        """Активация рабочего процесса"""
        return await self._make_request('POST', f'workflows/{workflow_id}/activate')
    
    async def deactivate_workflow(self, workflow_id: str) -> Dict:
        """Деактивация рабочего процесса"""
        return await self._make_request('POST', f'workflows/{workflow_id}/deactivate')
    
    async def execute_workflow(self, workflow_id: str, data: Optional[Dict] = None) -> Dict:
        """Запуск рабочего процесса"""
        payload = {"data": data} if data else {}
        return await self._make_request('POST', f'workflows/{workflow_id}/execute', payload)
    
    async def get_executions(self, workflow_id: Optional[str] = None, limit: int = 10) -> List[Dict]:
        """Получение списка выполнений"""
        endpoint = f'executions?limit={limit}'
        if workflow_id:
            endpoint += f'&workflowId={workflow_id}'
        
        result = await self._make_request('GET', endpoint)
        if 'error' in result:
            return []
        return result.get('data', [])
    
    async def get_execution_details(self, execution_id: str) -> Dict:
        """Получение деталей выполнения"""
        return await self._make_request('GET', f'executions/{execution_id}')
    
    async def stop_execution(self, execution_id: str) -> Dict:
        """Остановка выполнения"""
        return await self._make_request('POST', f'executions/{execution_id}/stop')
    
    async def get_health_status(self) -> Dict:
        """Проверка здоровья n8n"""
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    f"{self.base_url}/healthz",
                    timeout=aiohttp.ClientTimeout(total=10)
                ) as response:
                    return {
                        "status": "healthy" if response.status == 200 else "unhealthy",
                        "code": response.status
                    }
        except Exception as e:
            return {"status": "unreachable", "error": str(e)}
