from aiogram import Router

# Initialize router only once
router_instance = None

def get_router():
    global router_instance
    if router_instance is None:
        router_instance = Router()
    return router_instance