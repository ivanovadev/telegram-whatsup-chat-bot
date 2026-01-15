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
        self.openai_model = os.getenv("OPENAI_MODEL", "gpt-5.2")
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

IMPORTANT: These should be realistic job opportunities based on current market conditions. You will provide company names, job details, and we will create LinkedIn search links for users to find these positions.

IMPORTANT CONTEXT: These job posts will include motivational messages encouraging people that they can achieve their dream job. Make sure the vacancies are inspiring and represent great opportunities.

Requirements for EACH vacancy:
1. City: London (specifically Canary Wharf area)
2. Company location: Canary Wharf, London
3. Job title: Must be one of: DevOps Engineer, MLOps Engineer, SRE (Site Reliability Engineer), or System Engineer
4. Company rating: Must be > 4.0 (on a scale of 1-5)
5. Company restrictions: NOT a FAANG company (Facebook, Apple, Amazon, Netflix, Google), NOT a bank
6. AI-related keywords: The job description should mention AI-related work (e.g., "AI", "artificial intelligence", "machine learning", "ML", "MLOps", "AI models", "AI infrastructure", "AI systems", "AI platform", "AI tools", "AI solutions", "AI/ML", "ML pipelines", "AI deployment", etc.)
7. Salary: Between £60,000 and £110,000 per year (specify exact amount or range within this range)
8. Remote work: NOT remote (must be on-site or hybrid with office in Canary Wharf)

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
      "requirements": ["Requirement 1", "Requirement 2", "Requirement 3"]
    }},
    {{
      "company": "Company Name",
      "job_title": "DevOps Engineer / MLOps Engineer / SRE / System Engineer",
      "location": "Canary Wharf, London",
      "salary": "£60,000-£110,000 or range within this",
      "company_rating": 4.1-5.0,
      "description": "Brief job description (2-3 sentences)",
      "requirements": ["Requirement 1", "Requirement 2", "Requirement 3"]
    }},
    {{
      "company": "Company Name",
      "job_title": "DevOps Engineer / MLOps Engineer / SRE / System Engineer",
      "location": "Canary Wharf, London",
      "salary": "£60,000-£110,000 or range within this",
      "company_rating": 4.1-5.0,
      "description": "Brief job description (2-3 sentences)",
      "requirements": ["Requirement 1", "Requirement 2", "Requirement 3"]
    }}
  ]
}}

CRITICAL REQUIREMENTS:
- All vacancies should be REALISTIC based on current market conditions
- Companies should be real companies that typically hire in Canary Wharf
- Companies must NOT be FAANG (Facebook, Apple, Amazon, Netflix, Google), NOT banks
- Jobs MUST be AI-related: Descriptions should mention AI-related work (AI, artificial intelligence, machine learning, ML, MLOps, AI models, AI infrastructure, etc.)
- All jobs must be in Canary Wharf, London
- All salaries must be between £60,000 and £110,000 (realistic ranges within this bracket)
- All jobs must be on-site or hybrid with office in Canary Wharf (NOT fully remote)
- Company ratings must be > 4.0 (realistic estimate based on company reputation)
- Current date: {current_date}
- Note: LinkedIn search links will be auto-generated based on job title and location{used_context}

Return ONLY valid JSON, no additional text."""

            response = self.client.chat.completions.create(
                model=self.openai_model,
                messages=[
                    {"role": "system", "content": "You are a job market analyst specializing in tech jobs in Canary Wharf, London. Generate realistic job opportunities based on current market conditions. Focus on: 1) Real companies that typically hire in Canary Wharf for DevOps/MLOps/SRE roles. 2) Realistic salaries (£60k-£110k). 3) AI-related job descriptions (mention AI, ML, MLOps, AI infrastructure, etc.). 4) Accurate company information. Do NOT include FAANG companies or banks. Always return valid JSON only, no additional text."},
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
                
                # Add LinkedIn search URLs to each vacancy
                vacancies = data.get("vacancies", [])
                for vacancy in vacancies:
                    job_title = vacancy.get("job_title", "")
                    location = vacancy.get("location", "Canary Wharf, London")
                    # Generate LinkedIn search URL for this job
                    linkedin_url = self._generate_linkedin_search_url(job_title, location)
                    vacancy["linkedin_url"] = linkedin_url
                
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
    
    def _generate_linkedin_search_url(self, job_title: str, location: str) -> str:
        """Generate LinkedIn job search URL for given job title and location.
        
        URL includes filter for jobs posted in last 3 weeks (r1814400 = 21 days in seconds).
        """
        import urllib.parse
        
        # Clean and encode job title
        job_title_clean = job_title.strip()
        # Encode for URL
        keywords = urllib.parse.quote(job_title_clean)
        
        # Clean and encode location
        location_clean = location.strip()
        location_encoded = urllib.parse.quote(location_clean)
        
        # f_TPR=r1814400 means "posted in last 21 days" (3 weeks)
        # r604800 = 7 days, r1209600 = 14 days, r1814400 = 21 days
        url = f"https://www.linkedin.com/jobs/search/?keywords={keywords}&location={location_encoded}&f_TPR=r1814400"
        
        return url
    
    def _generate_template(self, used_companies: List[str]) -> Dict:
        """Generate template job content when LLM unavailable."""
        vacancies = [
            {
                "company": "Tech Solutions Ltd",
                "job_title": "DevOps Engineer",
                "location": "Canary Wharf, London",
                "salary": "£65,000-£90,000",
                "company_rating": 4.3,
                "description": "Looking for an experienced DevOps Engineer to join our infrastructure team. You will be responsible for maintaining and improving our cloud infrastructure and CI/CD pipelines.",
                "requirements": ["3+ years DevOps experience", "AWS/Azure knowledge", "Docker and Kubernetes"]
            },
            {
                "company": "Infrastructure Systems",
                "job_title": "SRE",
                "location": "Canary Wharf, London",
                "salary": "£75,000-£100,000",
                "company_rating": 4.5,
                "description": "Site Reliability Engineer needed to ensure high availability and performance of our systems. You will work on monitoring, automation, and incident response.",
                "requirements": ["5+ years SRE experience", "Linux/Unix systems", "Monitoring tools (Prometheus, Grafana)"]
            },
            {
                "company": "Engineering Corp",
                "job_title": "System Engineer",
                "location": "Canary Wharf, London",
                "salary": "£60,000-£85,000",
                "company_rating": 4.2,
                "description": "System Engineer position for maintaining and scaling our infrastructure. You will work with a team of engineers to ensure system reliability and performance.",
                "requirements": ["System administration experience", "Scripting (Python/Bash)", "Cloud platforms"]
            }
        ]
        
        # Add LinkedIn search URLs to each vacancy
        for vacancy in vacancies:
            job_title = vacancy.get("job_title", "")
            location = vacancy.get("location", "Canary Wharf, London")
            vacancy["linkedin_url"] = self._generate_linkedin_search_url(job_title, location)
        
        return {"vacancies": vacancies}
