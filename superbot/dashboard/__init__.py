"""
Dashboard package for SuperBot Trading Unifié.
"""
from .dashboard import DashboardServer, DashboardHandler, create_dashboard_data_func

Dashboard = DashboardServer

__all__ = [
    'Dashboard',
    'DashboardServer',
    'DashboardHandler',
    'create_dashboard_data_func'
]