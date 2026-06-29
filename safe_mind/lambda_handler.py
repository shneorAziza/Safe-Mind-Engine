from mangum import Mangum

from safe_mind.main import app


handler = Mangum(app, lifespan="auto")
