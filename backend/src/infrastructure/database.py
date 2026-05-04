"""
Prisma Client Singleton
=======================
Single source of truth for the Prisma ORM client.
Connected in lifespan.py; imported by repository layers.
"""

from prisma import Prisma

prisma = Prisma()
