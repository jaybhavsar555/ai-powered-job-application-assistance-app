"""Canonical job-board / portal URLs for Vault seeding."""

ATS_HOST_MARKERS = (
    "greenhouse.io",
    "lever.co",
    "ashbyhq.com",
    "myworkdayjobs.com",
)


def is_ats_host(host_or_url: str) -> bool:
    h = (host_or_url or "").lower()
    return any(m in h for m in ATS_HOST_MARKERS)


JOB_PORTALS = [
    # Major boards you browse daily — paste posting URL into Jobs → Import
    # (LinkedIn Easy Apply is never auto-submitted by Career OS)
    {
        "title": "LinkedIn Jobs",
        "url": "https://www.linkedin.com/jobs/",
        "region": "Global",
        "category": "major_board",
    },
    {
        "title": "Indeed",
        "url": "https://www.indeed.com/",
        "region": "Global",
        "category": "major_board",
    },
    {
        "title": "Indeed India",
        "url": "https://in.indeed.com/",
        "region": "India",
        "category": "major_board",
    },
    {
        "title": "Unstop",
        "url": "https://unstop.com/jobs",
        "region": "India",
        "category": "major_board",
    },
    {
        "title": "Naukri",
        "url": "https://www.naukri.com/",
        "region": "India",
        "category": "major_board",
    },
    {"title": "Remotive", "url": "https://remotive.com/remote-jobs", "region": "Remote"},
    {"title": "RemoteOK", "url": "https://remoteok.com/", "region": "Remote"},
    {"title": "Arbeitnow", "url": "https://www.arbeitnow.com/", "region": "Remote"},
    {"title": "Instahyre", "url": "https://www.instahyre.com/", "region": "India"},
    {"title": "Cutshort", "url": "https://cutshort.io/", "region": "India"},
    {"title": "Hirist", "url": "https://www.hirist.tech/", "region": "India"},
    {"title": "Foundit", "url": "https://www.foundit.in/", "region": "India"},
    {"title": "TopHire", "url": "https://tophire.co/", "region": "India"},
    {"title": "Weekday", "url": "https://www.weekday.works/", "region": "India"},
    {"title": "Y Combinator Jobs", "url": "https://www.ycombinator.com/jobs", "region": "Global"},
    {"title": "Wellfound", "url": "https://wellfound.com/jobs", "region": "Global"},
    {"title": "Startup.jobs", "url": "https://startup.jobs/", "region": "Global"},
    {"title": "We Work Remotely", "url": "https://weworkremotely.com/", "region": "Remote"},
    {"title": "FlexJobs", "url": "https://www.flexjobs.com/", "region": "Remote"},
    {"title": "Welcome to the Jungle", "url": "https://app.welcometothejungle.com/jobs", "region": "Global"},
    # ATS career-page hosts (company sites — best for extension autofill)
    {
        "title": "Greenhouse boards",
        "url": "https://boards.greenhouse.io/",
        "region": "Global",
        "category": "ats_career_page",
    },
    {
        "title": "Greenhouse job boards",
        "url": "https://job-boards.greenhouse.io/",
        "region": "Global",
        "category": "ats_career_page",
    },
    {
        "title": "Lever jobs",
        "url": "https://jobs.lever.co/",
        "region": "Global",
        "category": "ats_career_page",
    },
    {
        "title": "Ashby jobs",
        "url": "https://jobs.ashbyhq.com/",
        "region": "Global",
        "category": "ats_career_page",
    },
    {
        "title": "Workday jobs",
        "url": "https://www.myworkdayjobs.com/",
        "region": "Global",
        "category": "ats_career_page",
    },
]
