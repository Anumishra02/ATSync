from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from routes.resume import router as resume_router

app = FastAPI(title="AI Resume Analyzer")

app.add_middleware(
    CORSMiddleware,
    # allow_origins=["*"] let any site on the internet call this API from a
    # user's browser -- restricted to the actual frontend. The regex covers
    # Vercel preview deployments (verified against a real preview URL,
    # at-sync-ftrwbrje4-anumishra02s-projects.vercel.app, with fullmatch --
    # Starlette's CORSMiddleware itself uses fullmatch, not search, so this
    # can't be bypassed with an attacker-controlled prefix/suffix); if
    # Vercel's preview-URL format ever changes, re-verify against a real
    # preview before trusting it, the same way -- a regex that stops
    # matching fails silently as a plain CORS error, no server-side clue.
    allow_origins=["https://at-sync-zeta.vercel.app", "http://localhost:3000"],
    allow_origin_regex=r"https://at-sync-.*-anumishra02s-projects\.vercel\.app",
    allow_methods=["*"],
    allow_headers=["*"],
    # No cookies/auth in use -- must stay False, since allow_credentials=True
    # makes browsers reject a wildcard origin outright and would silently
    # break every one of the origins above if it were ever flipped on
    # without also switching every "*" here to an explicit list.
    allow_credentials=False,
)

app.include_router(resume_router, prefix="/api/resume")

@app.get("/")
def health_check():
    return {"status": "running", "message": "AI Resume Analyzer is live"}