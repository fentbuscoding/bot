# Massive amounts of imports in this project, so I put them all into one all-purpose imports file. Won't affect performance too much, moreso for ease of dev use

import aiohttp
import logging
import time
import discord
import json
import random
import sys
import os
import asyncio
import traceback
import signal
import atexit
import requests
import statistics
import math
from datetime import datetime
from discord.ext import commands, tasks
from os import system
from utils.command_tracker import usage_tracker
from utils.tos_handler import check_tos_acceptance, prompt_tos_acceptance
from utils.scalability import initialize_scalability
from pathlib import Path
from dataclasses import dataclass
from typing import Dict, List, Tuple, Optional