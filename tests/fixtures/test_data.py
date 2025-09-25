"""
Test data fixtures and generators for KuzuMemory tests.

Provides realistic test data, memory scenarios, and data generators
for comprehensive testing across all test suites.
"""

import random
from datetime import datetime, timedelta
from typing import List, Dict, Any, Generator
from dataclasses import dataclass

from kuzu_memory.core.models import Memory, MemoryType


@dataclass
class DataScenario:
    """Represents a complete test scenario with context."""
    name: str
    description: str
    user_id: str
    memories: List[Dict[str, Any]]
    queries: List[Dict[str, Any]]
    expected_outcomes: Dict[str, Any]


class DataGenerator:
    """Generates realistic test data for KuzuMemory testing."""
    
    def __init__(self, seed: int = 42):
        """Initialize with random seed for reproducible tests."""
        random.seed(seed)
        
        # Base data for generation
        self.names = [
            "Alice Johnson", "Bob Smith", "Carol Davis", "David Wilson", "Emma Brown",
            "Frank Miller", "Grace Lee", "Henry Taylor", "Ivy Chen", "Jack Anderson",
            "Kate Rodriguez", "Liam Garcia", "Maya Patel", "Noah Kim", "Olivia Martinez"
        ]
        
        self.companies = [
            "TechCorp", "DataFlow Inc", "CloudSoft Solutions", "InnovateTech LLC",
            "DigitalFirst", "SmartSystems", "NextGen Technologies", "FutureTech",
            "CodeCraft", "DevOps Masters", "AI Innovations", "WebScale Solutions"
        ]
        
        self.technologies = [
            "Python", "JavaScript", "TypeScript", "Java", "Go", "Rust", "C++",
            "React", "Vue.js", "Angular", "Django", "Flask", "FastAPI", "Spring Boot",
            "PostgreSQL", "MongoDB", "Redis", "MySQL", "Docker", "Kubernetes",
            "AWS", "Azure", "GCP", "Jenkins", "GitHub Actions", "Terraform"
        ]
        
        self.projects = [
            "User Authentication System", "Payment Processing Module", "Data Analytics Dashboard",
            "Customer Insights Platform", "Inventory Management System", "Real-time Chat Application",
            "E-commerce Backend", "Mobile API Gateway", "Machine Learning Pipeline",
            "Content Management System", "Monitoring Dashboard", "Notification Service"
        ]
        
        self.roles = [
            "Software Engineer", "Senior Developer", "Tech Lead", "Principal Engineer",
            "Data Scientist", "DevOps Engineer", "Full Stack Developer", "Backend Developer",
            "Frontend Developer", "System Architect", "Engineering Manager", "CTO"
        ]
    
    def generate_identity_memory(self, user_id: str = None) -> Dict[str, Any]:
        """Generate an identity-related memory."""
        name = random.choice(self.names)
        company = random.choice(self.companies)
        role = random.choice(self.roles)
        
        templates = [
            f"My name is {name} and I work at {company} as a {role}.",
            f"I'm {name}, currently employed at {company} in the {role} position.",
            f"Hi, I'm {name}. I'm a {role} at {company}.",
            f"You can call me {name}. I work as a {role} for {company}.",
        ]
        
        return {
            "content": random.choice(templates),
            "user_id": user_id or f"user-{hash(name) % 1000}",
            "session_id": "identity-session",
            "source": "profile",
            "memory_type": MemoryType.IDENTITY,
            "entities": [name, company, role]
        }
    
    def generate_preference_memory(self, user_id: str = None) -> Dict[str, Any]:
        """Generate a preference-related memory."""
        tech1 = random.choice(self.technologies)
        tech2 = random.choice(self.technologies)
        
        templates = [
            f"I prefer {tech1} for backend development and {tech2} for frontend.",
            f"I like using {tech1} because it's reliable and efficient.",
            f"I always use {tech1} for this type of project.",
            f"My favorite technology stack includes {tech1} and {tech2}.",
            f"I don't like {tech1}, I prefer {tech2} instead.",
            f"I usually choose {tech1} over {tech2} for performance reasons.",
        ]
        
        return {
            "content": random.choice(templates),
            "user_id": user_id or "preference-user",
            "session_id": "preference-session",
            "source": "conversation",
            "memory_type": MemoryType.PREFERENCE,
            "entities": [tech1, tech2]
        }
    
    def generate_decision_memory(self, user_id: str = None) -> Dict[str, Any]:
        """Generate a decision-related memory."""
        tech = random.choice(self.technologies)
        project = random.choice(self.projects)
        
        templates = [
            f"We decided to use {tech} for the {project}.",
            f"After discussion, we chose {tech} as our main technology.",
            f"The team agreed to implement {project} using {tech}.",
            f"We're going with {tech} for better performance in {project}.",
            f"The decision is to migrate {project} to {tech}.",
        ]
        
        return {
            "content": random.choice(templates),
            "user_id": user_id or "decision-user",
            "session_id": "decision-session",
            "source": "meeting",
            "memory_type": MemoryType.DECISION,
            "entities": [tech, project]
        }
    
    def generate_status_memory(self, user_id: str = None) -> Dict[str, Any]:
        """Generate a status-related memory."""
        project = random.choice(self.projects)
        tech = random.choice(self.technologies)
        
        templates = [
            f"Currently working on the {project} using {tech}.",
            f"I'm debugging the {project} implementation.",
            f"Making progress on {project} - almost done with the core features.",
            f"Started implementing {project} with {tech} this week.",
            f"The {project} is in testing phase now.",
        ]
        
        return {
            "content": random.choice(templates),
            "user_id": user_id or "status-user",
            "session_id": "status-session",
            "source": "status_update",
            "memory_type": MemoryType.STATUS,
            "entities": [project, tech]
        }
    
    def generate_pattern_memory(self, user_id: str = None) -> Dict[str, Any]:
        """Generate a pattern/best practice memory."""
        templates = [
            "Always validate input data before processing.",
            "Never use global variables in production code.",
            "Remember to write unit tests for all new features.",
            "Always use environment variables for configuration.",
            "Implement proper error handling and logging.",
            "Use meaningful variable and function names.",
            "Keep functions small and focused on single responsibility.",
            "Always review code before merging to main branch.",
        ]
        
        return {
            "content": random.choice(templates),
            "user_id": user_id or "pattern-user",
            "session_id": "best-practices",
            "source": "guidelines",
            "memory_type": MemoryType.PATTERN,
            "entities": []
        }
    
    def generate_solution_memory(self, user_id: str = None) -> Dict[str, Any]:
        """Generate a solution-related memory."""
        tech = random.choice(self.technologies)
        
        templates = [
            f"To fix the performance issue, we optimized the {tech} queries.",
            f"The bug was caused by incorrect {tech} configuration - fixed by updating settings.",
            f"Resolved the deployment issue by updating the {tech} version.",
            f"Fixed the memory leak by properly closing {tech} connections.",
            f"The authentication problem was solved by updating {tech} middleware.",
        ]
        
        return {
            "content": random.choice(templates),
            "user_id": user_id or "solution-user",
            "session_id": "problem-solving",
            "source": "troubleshooting",
            "memory_type": MemoryType.SOLUTION,
            "entities": [tech]
        }
    
    def generate_memory_batch(self, count: int, user_id: str = None, 
                            memory_types: List[MemoryType] = None) -> List[Dict[str, Any]]:
        """Generate a batch of diverse memories."""
        if memory_types is None:
            memory_types = list(MemoryType)
        
        generators = {
            MemoryType.IDENTITY: self.generate_identity_memory,
            MemoryType.PREFERENCE: self.generate_preference_memory,
            MemoryType.DECISION: self.generate_decision_memory,
            MemoryType.STATUS: self.generate_status_memory,
            MemoryType.PATTERN: self.generate_pattern_memory,
            MemoryType.SOLUTION: self.generate_solution_memory,
        }
        
        memories = []
        for i in range(count):
            memory_type = random.choice(memory_types)
            generator = generators.get(memory_type, self.generate_preference_memory)
            memory_data = generator(user_id)
            memory_data["batch_index"] = i
            memories.append(memory_data)
        
        return memories
    
    def generate_test_scenario(self, scenario_name: str) -> DataScenario:
        """Generate a complete test scenario."""
        scenarios = {
            "software_engineer": self._generate_software_engineer_scenario,
            "data_scientist": self._generate_data_scientist_scenario,
            "devops_engineer": self._generate_devops_engineer_scenario,
            "startup_founder": self._generate_startup_founder_scenario,
            "team_collaboration": self._generate_team_collaboration_scenario,
        }
        
        generator = scenarios.get(scenario_name, self._generate_software_engineer_scenario)
        return generator()
    
    def _generate_software_engineer_scenario(self) -> DataScenario:
        """Generate a software engineer test scenario."""
        user_id = "alice-engineer"
        
        memories = [
            {
                "content": "My name is Alice Johnson and I work at TechCorp as a Senior Software Engineer.",
                "user_id": user_id,
                "session_id": "profile",
                "source": "introduction",
                "memory_type": MemoryType.IDENTITY
            },
            {
                "content": "I prefer Python for backend development and React for frontend applications.",
                "user_id": user_id,
                "session_id": "tech-preferences",
                "source": "conversation",
                "memory_type": MemoryType.PREFERENCE
            },
            {
                "content": "We decided to use PostgreSQL as our main database with Redis for caching.",
                "user_id": user_id,
                "session_id": "architecture-meeting",
                "source": "meeting",
                "memory_type": MemoryType.DECISION
            },
            {
                "content": "Currently working on the user authentication microservice using FastAPI.",
                "user_id": user_id,
                "session_id": "daily-standup",
                "source": "status_update",
                "memory_type": MemoryType.STATUS
            },
            {
                "content": "Always write comprehensive unit tests before deploying to production.",
                "user_id": user_id,
                "session_id": "best-practices",
                "source": "guidelines",
                "memory_type": MemoryType.PATTERN
            }
        ]
        
        queries = [
            {
                "query": "What's my name and where do I work?",
                "expected_memories": 1,
                "expected_entities": ["Alice Johnson", "TechCorp"]
            },
            {
                "query": "What technologies do I prefer?",
                "expected_memories": 1,
                "expected_entities": ["Python", "React"]
            },
            {
                "query": "What database are we using?",
                "expected_memories": 1,
                "expected_entities": ["PostgreSQL", "Redis"]
            },
            {
                "query": "What am I currently working on?",
                "expected_memories": 1,
                "expected_entities": ["authentication", "FastAPI"]
            }
        ]
        
        return DataScenario(
            name="software_engineer",
            description="Complete software engineer profile and work scenario",
            user_id=user_id,
            memories=memories,
            queries=queries,
            expected_outcomes={
                "total_memories": len(memories),
                "memory_types": {mt.value for mt in [m["memory_type"] for m in memories]},
                "recall_success_rate": 1.0
            }
        )
    
    def _generate_data_scientist_scenario(self) -> DataScenario:
        """Generate a data scientist test scenario."""
        user_id = "dr-sarah-data"
        
        memories = [
            {
                "content": "I'm Dr. Sarah Chen, a Senior Data Scientist at DataFlow Inc.",
                "user_id": user_id,
                "session_id": "profile",
                "source": "introduction",
                "memory_type": MemoryType.IDENTITY
            },
            {
                "content": "I prefer Python with scikit-learn and TensorFlow for machine learning projects.",
                "user_id": user_id,
                "session_id": "ml-discussion",
                "source": "conversation",
                "memory_type": MemoryType.PREFERENCE
            },
            {
                "content": "We decided to use Apache Spark for big data processing in our ML pipeline.",
                "user_id": user_id,
                "session_id": "architecture-review",
                "source": "meeting",
                "memory_type": MemoryType.DECISION
            },
            {
                "content": "Currently training a sentiment analysis model on customer feedback data.",
                "user_id": user_id,
                "session_id": "project-update",
                "source": "status_update",
                "memory_type": MemoryType.STATUS
            }
        ]
        
        queries = [
            {
                "query": "What's my background and expertise?",
                "expected_memories": 1,
                "expected_entities": ["Sarah Chen", "Data Scientist"]
            },
            {
                "query": "What ML frameworks do I use?",
                "expected_memories": 1,
                "expected_entities": ["scikit-learn", "TensorFlow"]
            },
            {
                "query": "What's our big data solution?",
                "expected_memories": 1,
                "expected_entities": ["Apache Spark"]
            }
        ]
        
        return DataScenario(
            name="data_scientist",
            description="Data scientist with ML focus scenario",
            user_id=user_id,
            memories=memories,
            queries=queries,
            expected_outcomes={
                "total_memories": len(memories),
                "memory_types": {mt.value for mt in [m["memory_type"] for m in memories]},
                "recall_success_rate": 1.0
            }
        )
    
    def _generate_devops_engineer_scenario(self) -> DataScenario:
        """Generate a DevOps engineer test scenario."""
        user_id = "mike-devops"
        
        memories = [
            {
                "content": "I'm Mike Rodriguez, a DevOps Engineer at CloudTech Solutions.",
                "user_id": user_id,
                "session_id": "profile",
                "source": "introduction",
                "memory_type": MemoryType.IDENTITY
            },
            {
                "content": "I prefer Infrastructure as Code using Terraform and Ansible for automation.",
                "user_id": user_id,
                "session_id": "iac-discussion",
                "source": "conversation",
                "memory_type": MemoryType.PREFERENCE
            },
            {
                "content": "We decided to migrate all services to Kubernetes for better scalability.",
                "user_id": user_id,
                "session_id": "migration-planning",
                "source": "meeting",
                "memory_type": MemoryType.DECISION
            },
            {
                "content": "Currently setting up monitoring with Prometheus and Grafana.",
                "user_id": user_id,
                "session_id": "monitoring-setup",
                "source": "status_update",
                "memory_type": MemoryType.STATUS
            }
        ]
        
        queries = [
            {
                "query": "What's my role and company?",
                "expected_memories": 1,
                "expected_entities": ["Mike Rodriguez", "DevOps Engineer"]
            },
            {
                "query": "What tools do I use for infrastructure?",
                "expected_memories": 1,
                "expected_entities": ["Terraform", "Ansible"]
            },
            {
                "query": "What's our container strategy?",
                "expected_memories": 1,
                "expected_entities": ["Kubernetes"]
            }
        ]
        
        return DataScenario(
            name="devops_engineer",
            description="DevOps engineer with infrastructure focus",
            user_id=user_id,
            memories=memories,
            queries=queries,
            expected_outcomes={
                "total_memories": len(memories),
                "memory_types": {mt.value for mt in [m["memory_type"] for m in memories]},
                "recall_success_rate": 1.0
            }
        )
    
    def _generate_startup_founder_scenario(self) -> DataScenario:
        """Generate a startup founder test scenario."""
        user_id = "emma-founder"
        
        memories = [
            {
                "content": "I'm Emma Wilson, founder and CTO of InnovateTech, a fintech startup.",
                "user_id": user_id,
                "session_id": "profile",
                "source": "introduction",
                "memory_type": MemoryType.IDENTITY
            },
            {
                "content": "We decided to build our platform using microservices with Node.js and MongoDB.",
                "user_id": user_id,
                "session_id": "tech-stack-decision",
                "source": "meeting",
                "memory_type": MemoryType.DECISION
            },
            {
                "content": "Currently raising Series A funding and expanding the engineering team.",
                "user_id": user_id,
                "session_id": "business-update",
                "source": "status_update",
                "memory_type": MemoryType.STATUS
            }
        ]
        
        queries = [
            {
                "query": "What's my company and role?",
                "expected_memories": 1,
                "expected_entities": ["Emma Wilson", "InnovateTech", "CTO"]
            },
            {
                "query": "What's our technology stack?",
                "expected_memories": 1,
                "expected_entities": ["Node.js", "MongoDB"]
            },
            {
                "query": "What's our current business status?",
                "expected_memories": 1,
                "expected_entities": ["Series A", "funding"]
            }
        ]
        
        return DataScenario(
            name="startup_founder",
            description="Startup founder with business and technical responsibilities",
            user_id=user_id,
            memories=memories,
            queries=queries,
            expected_outcomes={
                "total_memories": len(memories),
                "memory_types": {mt.value for mt in [m["memory_type"] for m in memories]},
                "recall_success_rate": 1.0
            }
        )
    
    def _generate_team_collaboration_scenario(self) -> DataScenario:
        """Generate a team collaboration test scenario."""
        return DataScenario(
            name="team_collaboration",
            description="Multi-user team collaboration scenario",
            user_id="team-lead",
            memories=[],  # Will be populated with multiple users
            queries=[],
            expected_outcomes={}
        )


# Global test data generator instance
test_data_generator = DataGenerator()


def get_test_scenario(scenario_name: str) -> DataScenario:
    """Get a predefined test scenario."""
    return test_data_generator.generate_test_scenario(scenario_name)


def generate_test_memories(count: int, user_id: str = None, 
                         memory_types: List[MemoryType] = None) -> List[Dict[str, Any]]:
    """Generate test memories."""
    return test_data_generator.generate_memory_batch(count, user_id, memory_types)


def generate_performance_test_data(memory_count: int, user_count: int = 1) -> List[Dict[str, Any]]:
    """Generate data for performance testing."""
    all_memories = []
    
    for user_idx in range(user_count):
        user_id = f"perf-user-{user_idx}"
        memories_per_user = memory_count // user_count
        
        user_memories = test_data_generator.generate_memory_batch(
            memories_per_user, 
            user_id
        )
        all_memories.extend(user_memories)
    
    return all_memories
