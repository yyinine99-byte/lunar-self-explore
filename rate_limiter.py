"""简易限流器 - 基于内存的滑动窗口限流。

用于防止单个 IP 短时间大量调用 AI API。
"""

import time
from collections import defaultdict
from typing import Dict, List


class RateLimiter:
    def __init__(self, max_requests: int = 20, window_seconds: int = 3600):
        """初始化限流器。

        Args:
            max_requests: 窗口内最大请求数
            window_seconds: 时间窗口（秒），默认1小时
        """
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self._storage: Dict[str, List[float]] = defaultdict(list)

    def allow(self, key: str) -> bool:
        """检查是否允许请求。"""
        now = time.time()
        window_start = now - self.window_seconds

        # 清理过期记录
        self._storage[key] = [t for t in self._storage[key] if t > window_start]

        if len(self._storage[key]) >= self.max_requests:
            return False

        self._storage[key].append(now)
        return True

    def remaining(self, key: str) -> int:
        """返回剩余配额。"""
        now = time.time()
        window_start = now - self.window_seconds
        self._storage[key] = [t for t in self._storage[key] if t > window_start]
        return max(0, self.max_requests - len(self._storage[key]))


# 全局限流器实例
chat_limiter = RateLimiter(max_requests=30, window_seconds=3600)  # 每小时30次对话
chart_limiter = RateLimiter(max_requests=60, window_seconds=3600)  # 每小时60次计算
