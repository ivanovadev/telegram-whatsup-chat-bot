"""Generate content for job posts."""
import os
import logging
import random
from typing import Dict, Optional, List
from openai import OpenAI
from datetime import datetime

logger = logging.getLogger(__name__)


class JobContentGenerator:
    """Generate job vacancy content."""
    
    JOB_TITLES = ["DevOps Engineer", "MLOps Engineer", "SRE (Site Reliability Engineer)", "System Engineer"]
    
    def __init__(self, budget_guard):
        """Initialize job content generator."""
        self.budget_guard = budget_guard
        self.openai_api_key = os.getenv("OPENAI_API_KEY", "")
        self.openai_model = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
        self.llm_enabled = os.getenv("LLM_ENABLED", "off").lower() == "on"
        
        if self.llm_enabled and self.openai_api_key:
            self.client = OpenAI(api_key=self.openai_api_key)
        else:
            self.client = None
            logger.warning("LLM disabled for job content")
    
    def generate_job_post(self, used_companies: List[str] = None) -> Optional[Dict]:
        """Generate job post with 3 vacancies."""
        used_companies = used_companies or []
        
        if self.client and self.llm_enabled:
            return self._generate_with_llm(used_companies)
        else:
            return self._generate_template(used_companies)
    
    def _generate_with_llm(self, used_companies: List[str]) -> Optional[Dict]:
        """Generate job content using LLM."""
        try:
            current_date = datetime.now().strftime("%Y-%m-%d")
            
            used_context = ""
            if used_companies:
                used_context = f"\n\nAvoid companies that were recently used: {', '.join(used_companies[-5:])}"
            
            prompt = f"""Generate 3 REAL and CURRENT job vacancies in London, Canary Wharf area.

CRITICAL: You MUST search LinkedIn Jobs (linkedin.com/jobs) for ACTUAL current job postings that match these criteria. 

IMPORTANT URL VALIDATION:
- You MUST verify that each LinkedIn job URL is REAL and ACTIVE before including it
- The job posting MUST be currently active (not expired, not deleted, not closed)
- The job ID in the URL MUST be valid and correspond to an existing job posting
- Test each URL: it must load successfully and show the actual job posting page
- If a job posting was deleted or expired, DO NOT include it - find a different one
- Only use job postings that you have personally verified exist and are accessible RIGHT NOW

Do NOT make up or generate fake job postings. Do NOT use expired or deleted job postings. Only use REAL, ACTIVE job postings that exist on LinkedIn RIGHT NOW and can be accessed.

IMPORTANT CONTEXT: These job posts will include motivational messages encouraging people that they can achieve their dream job. Make sure the vacancies are inspiring and represent great opportunities.

Requirements for EACH vacancy:
1. City: London (specifically Canary Wharf area)
2. Company location: Canary Wharf, London
3. Job title: Must be one of: DevOps Engineer, MLOps Engineer, SRE (Site Reliability Engineer), or System Engineer
4. Company rating: Must be > 4.0 (on a scale of 1-5)
5. Company restrictions: NOT a FAANG company (Facebook, Apple, Amazon, Netflix, Google), NOT a bank
6. AI-related keywords: The job posting MUST contain AI-related keywords in the LinkedIn job description (e.g., "AI", "artificial intelligence", "machine learning", "ML", "MLOps", "AI models", "AI infrastructure", "AI systems", "AI platform", "AI tools", "AI solutions", "AI/ML", "ML pipelines", "AI deployment", etc.). Verify that the LinkedIn job description mentions AI-related work.
7. Salary: Between £60,000 and £110,000 per year (specify exact amount or range within this range)
8. Remote work: NOT remote (must be on-site or hybrid with office in Canary Wharf)
9. LinkedIn link: MUST be a REAL, ACTIVE LinkedIn job posting URL from linkedin.com/jobs/view/... or linkedin.com/jobs/search/... that you have VERIFIED exists. The URL must be clickable and lead to an actual job posting.

Format as JSON:
{{
  "vacancies": [
    {{
      "company": "Company Name",
      "job_title": "DevOps Engineer / MLOps Engineer / SRE / System Engineer",
      "location": "Canary Wharf, London",
      "salary": "£60,000-£110,000 or range within this (e.g., £65,000-£85,000)",
      "company_rating": 4.1-5.0,
      "description": "Brief job description (2-3 sentences)",
      "requirements": ["Requirement 1", "Requirement 2", "Requirement 3"],
      "linkedin_url": "https://www.linkedin.com/jobs/view/..."
    }},
    {{
      "company": "Company Name",
      "job_title": "DevOps Engineer / MLOps Engineer / SRE / System Engineer",
      "location": "Canary Wharf, London",
      "salary": "£60,000-£110,000 or range within this",
      "company_rating": 4.1-5.0,
      "description": "Brief job description (2-3 sentences)",
      "requirements": ["Requirement 1", "Requirement 2", "Requirement 3"],
      "linkedin_url": "https://www.linkedin.com/jobs/view/..."
    }},
    {{
      "company": "Company Name",
      "job_title": "DevOps Engineer / MLOps Engineer / SRE / System Engineer",
      "location": "Canary Wharf, London",
      "salary": "£60,000-£110,000 or range within this",
      "company_rating": 4.1-5.0,
      "description": "Brief job description (2-3 sentences)",
      "requirements": ["Requirement 1", "Requirement 2", "Requirement 3"],
      "linkedin_url": "https://www.linkedin.com/jobs/view/..."
    }}
  ]
}}

CRITICAL REQUIREMENTS:
- You MUST search LinkedIn Jobs (linkedin.com/jobs) and find REAL, ACTIVE job postings
- All vacancies MUST be REAL and CURRENT (posted within last 7 days, still active and accessible)
- LinkedIn URLs MUST be REAL job posting URLs that you have verified exist and are accessible RIGHT NOW
- Format: https://www.linkedin.com/jobs/view/XXXXXXXXXX/ (preferred) or https://www.linkedin.com/jobs/collections/recommended/?currentJobId=XXXXXXXXXX
- CRITICAL: Test each URL before including it - it must load successfully and show the actual job posting page
- If a job posting shows "This job may no longer be available" or "Unable to load page" or "Job ID may be invalid" - DO NOT include it
- If you cannot verify a job posting is active and accessible, find a different one
- Only include job postings that you have personally verified are currently active and accessible
- Companies must NOT be FAANG (Facebook, Apple, Amazon, Netflix, Google), NOT banks
- Jobs MUST be AI-related: The LinkedIn job posting description MUST contain AI-related keywords (AI, artificial intelligence, machine learning, ML, MLOps, AI models, AI infrastructure, AI systems, AI platform, AI tools, AI solutions, AI/ML, ML pipelines, AI deployment, etc.). Verify this in the actual LinkedIn job posting before including it.
- All jobs must be in Canary Wharf, London (verify location in job posting)
- All salaries must be between £60,000 and £110,000 (verify in job posting, prefer range within this bracket)
- All jobs must be on-site or hybrid with office in Canary Wharf (NOT fully remote)
- Company ratings must be > 4.0 (you can estimate based on company reputation)
- DO NOT generate fake job IDs or make up URLs
- Current date: {current_date}{used_context}

Return ONLY valid JSON, no additional text."""

            response = self.client.chat.completions.create(
                model=self.openai_model,
                messages=[
                    {"role": "system", "content": "You are a job search specialist with access to LinkedIn Jobs. You MUST search for REAL, ACTIVE job postings on LinkedIn (linkedin.com/jobs) that match the criteria. CRITICAL REQUIREMENTS: 1) Each job posting MUST contain AI-related keywords in its description (AI, artificial intelligence, machine learning, ML, MLOps, AI models, AI infrastructure, etc.). 2) Each LinkedIn URL MUST be verified as REAL, ACTIVE, and ACCESSIBLE - test each URL to ensure it loads successfully and shows the actual job posting page. 3) Do NOT use expired, deleted, or inaccessible job postings. 4) If a job posting cannot be verified as active and accessible, find a different one. 5) Only use job postings posted within the last 7 days that are still active. Never generate fake job IDs or URLs. Always verify that each LinkedIn URL leads to a real, accessible job posting before including it. Always return valid JSON only, no additional text."},
                    {"role": "user", "content": prompt}
                ],
                max_completion_tokens=1500,
                response_format={"type": "json_object"}
            )
            
            import json
            import re
            content = response.choices[0].message.content.strip()
            
            # Try to extract JSON if wrapped in markdown code blocks
            json_match = re.search(r'```(?:json)?\s*(\{.*?\})\s*```', content, re.DOTALL)
            if json_match:
                content = json_match.group(1)
            
            # Try to find JSON object in the response
            if not content.startswith('{'):
                json_match = re.search(r'\{.*\}', content, re.DOTALL)
                if json_match:
                    content = json_match.group(0)
            
            # Validate and parse JSON
            if not content or not content.strip():
                logger.error("Empty response from LLM for jobs")
                return self._generate_template(used_companies)
            
            try:
                data = json.loads(content)
                
                # Validate LinkedIn URLs - filter out invalid ones
                vacancies = data.get("vacancies", [])
                valid_vacancies = []
                for vacancy in vacancies:
                    linkedin_url = vacancy.get("linkedin_url", "")
                    if linkedin_url:
                        # Validate URL format
                        if not linkedin_url.startswith("https://www.linkedin.com/jobs"):
                            logger.warning(f"Invalid LinkedIn URL format: {linkedin_url}")
                            # Try to fix common issues
                            if "linkedin.com" in linkedin_url:
                                if not linkedin_url.startswith("http"):
                                    linkedin_url = "https://" + linkedin_url
                                # Check if it's a valid LinkedIn jobs URL after fixing
                                if linkedin_url.startswith("https://www.linkedin.com/jobs"):
                                    vacancy["linkedin_url"] = linkedin_url
                                    valid_vacancies.append(vacancy)
                                else:
                                    logger.warning(f"Removing invalid LinkedIn URL (not a jobs URL): {linkedin_url}")
                            else:
                                logger.warning(f"Removing invalid LinkedIn URL (not LinkedIn): {linkedin_url}")
                        else:
                            # URL format is valid, include vacancy
                            valid_vacancies.append(vacancy)
                    else:
                        logger.warning("Vacancy missing LinkedIn URL, skipping")
                
                # Update data with only valid vacancies
                if valid_vacancies:
                    data["vacancies"] = valid_vacancies
                else:
                    logger.error("No valid vacancies found after URL validation")
                    return self._generate_template(used_companies)
                
            except json.JSONDecodeError as e:
                logger.error(f"JSON decode error for jobs: {e}. Content: {content[:200]}")
                try:
                    content = content[content.find('{'):]
                    content = content[:content.rfind('}') + 1]
                    data = json.loads(content)
                except Exception as e2:
                    logger.error(f"Failed to fix JSON for jobs: {e2}")
                    return self._generate_template(used_companies)
            
            # Record usage
            tokens_used = response.usage.total_tokens
            cost_per_1k = 0.15 / 1000
            estimated_cost = (tokens_used / 1000) * cost_per_1k
            self.budget_guard.record_llm_call(tokens_used, estimated_cost)
            
            return data
            
        except Exception as e:
            logger.error(f"LLM error generating job content: {e}")
            return self._generate_template(used_companies)
    
    def _generate_template(self, used_companies: List[str]) -> Dict:
        """Generate template job content when LLM unavailable."""
        return {
            "vacancies": [
                {
                    "company": "Tech Solutions Ltd",
                    "job_title": "DevOps Engineer",
                    "location": "Canary Wharf, London",
                    "salary": "£65,000-£90,000",
                    "company_rating": 4.3,
                    "description": "Looking for an experienced DevOps Engineer to join our infrastructure team. You will be responsible for maintaining and improving our cloud infrastructure and CI/CD pipelines.",
                    "requirements": ["3+ years DevOps experience", "AWS/Azure knowledge", "Docker and Kubernetes"],
                    "linkedin_url": "https://www.linkedin.com/jobs/view/example1"
                },
                {
                    "company": "Infrastructure Systems",
                    "job_title": "SRE",
                    "location": "Canary Wharf, London",
                    "salary": "£75,000-£100,000",
                    "company_rating": 4.5,
                    "description": "Site Reliability Engineer needed to ensure high availability and performance of our systems. You will work on monitoring, automation, and incident response.",
                    "requirements": ["5+ years SRE experience", "Linux/Unix systems", "Monitoring tools (Prometheus, Grafana)"],
                    "linkedin_url": "https://www.linkedin.com/jobs/view/example2"
                },
                {
                    "company": "Engineering Corp",
                    "job_title": "System Engineer",
                    "location": "Canary Wharf, London",
                    "salary": "£60,000-£85,000",
                    "company_rating": 4.2,
                    "description": "System Engineer position for maintaining and scaling our infrastructure. You will work with a team of engineers to ensure system reliability and performance.",
                    "requirements": ["System administration experience", "Scripting (Python/Bash)", "Cloud platforms"],
                    "linkedin_url": "https://www.linkedin.com/jobs/view/example3"
                }
            ]
        }
