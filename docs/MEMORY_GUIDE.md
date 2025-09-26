# KuzuMemory - Memory System Guide

**How to use the .claude-mpm memory system for optimal AI agent performance**

---

## 🧠 **Memory System Overview**

The `.claude-mpm/memories/` directory contains specialized memory files that help AI agents understand and work with the KuzuMemory project effectively. Each file serves a specific role in the agent specialization system.

---

## 📁 **Memory File Structure**

```
.claude-mpm/memories/
├── PM.md           # Project Management memory
├── engineer.md     # Engineering implementation patterns
├── qa.md          # Quality Assurance testing strategies
└── MEMORY_GUIDE.md # This file - explains memory usage
```

---

## 🎯 **Memory File Purposes**

### **PM.md - Project Management Memory**
- **Purpose**: High-level project overview and coordination
- **Contains**: Architecture overview, key technologies, development standards
- **Use when**: Need project context, standards, or coordination information
- **Target agents**: Project managers, coordinators, documentation specialists

### **engineer.md - Engineering Implementation Patterns**
- **Purpose**: Deep technical implementation knowledge
- **Contains**: Code patterns, architecture details, performance optimizations
- **Use when**: Implementing features, debugging, optimizing performance
- **Target agents**: Software engineers, architects, performance specialists

### **qa.md - Quality Assurance Testing Strategies**
- **Purpose**: Testing approaches and quality standards
- **Contains**: Test patterns, performance targets, validation strategies
- **Use when**: Writing tests, validating functionality, ensuring quality
- **Target agents**: QA engineers, test automation specialists, quality assurance

---

## 🔄 **Memory Usage Patterns**

### **Agent Role Selection**
Choose memory files based on your current task:

```
🏗️  Project Management Tasks → PM.md
    • Project overview questions
    • Standards and conventions
    • Architecture decisions
    • Team coordination

💻 Engineering Tasks → engineer.md
    • Code implementation
    • Performance optimization
    • Architecture patterns
    • Technical debugging

🧪 Quality Assurance Tasks → qa.md
    • Test implementation
    • Performance validation
    • Quality standards
    • Testing strategies
```

### **Cross-Role Information Sharing**
Some tasks require multiple memory files:

- **Feature Implementation**: PM.md (requirements) + engineer.md (implementation)
- **Performance Optimization**: engineer.md (patterns) + qa.md (benchmarks)
- **Documentation Updates**: PM.md (standards) + engineer.md (technical details)

---

## 💡 **Best Practices for Memory Usage**

### **1. Memory File Selection**
- Start with PM.md for project context
- Use engineer.md for implementation details
- Reference qa.md for testing and validation
- Always check MEMORY_GUIDE.md for usage instructions

### **2. Information Layering**
- **PM.md**: Strategic and architectural level
- **engineer.md**: Tactical implementation level
- **qa.md**: Validation and quality level
- **This guide**: Meta-level (how to use the system)

### **3. Update Procedures**
When working on the project, update relevant memory files:

```bash
# After implementing new features
# Update engineer.md with new patterns

# After changing project standards
# Update PM.md with new requirements

# After adding test strategies
# Update qa.md with new approaches
```

---

## 🎯 **Memory Content Guidelines**

### **What to Include in Each Memory File**

#### **PM.md Should Contain:**
- Project architecture overview
- Key technologies and decisions
- Development standards and conventions
- Critical performance targets
- Single-path workflow commands
- AI integration patterns

#### **engineer.md Should Contain:**
- Implementation patterns and best practices
- Code structure and organization
- Performance optimization techniques
- Database schema and operations
- Error handling strategies
- Configuration management patterns

#### **qa.md Should Contain:**
- Testing strategies and approaches
- Performance benchmarks and targets
- Quality metrics and coverage goals
- Test fixture patterns
- Validation procedures
- Regression testing strategies

### **What to Avoid**
- **Duplicate information** across files (maintain single source of truth)
- **Outdated information** (keep memories current with codebase)
- **Generic advice** (focus on project-specific knowledge)
- **Implementation details in PM.md** (belongs in engineer.md)
- **High-level strategy in qa.md** (belongs in PM.md)

---

## 🔧 **Memory Maintenance**

### **Regular Updates**
Update memory files when:
- Architecture changes significantly
- New patterns emerge from development
- Performance targets are modified
- Testing strategies evolve
- Standards or conventions change

### **Quality Checks**
Ensure memory files:
- Reflect current project state
- Contain accurate technical information
- Follow the same priority system (🔴 → 🟡 → 🟢 → ⚪)
- Include specific, actionable information
- Avoid contradicting other memory files

### **Consistency Validation**
Check that:
- Performance targets match across files
- Command examples work as documented
- Architecture descriptions align
- Standards are consistently applied

---

## 🚀 **Advanced Memory Usage**

### **Memory Combination Strategies**
For complex tasks, use multiple memories:

```
Feature Development Workflow:
1. PM.md → Understand requirements and standards
2. engineer.md → Learn implementation patterns
3. qa.md → Plan testing strategy
4. Implement with full context

Performance Optimization Workflow:
1. PM.md → Check performance targets
2. engineer.md → Review optimization patterns
3. qa.md → Understand benchmark requirements
4. Optimize with measurable goals
```

### **Memory-Driven Development**
Use memories to guide development:
- Check PM.md before starting any task
- Reference engineer.md during implementation
- Validate against qa.md standards
- Update memories with new learnings

---

## 📊 **Memory Effectiveness Metrics**

### **Success Indicators**
- Agents can quickly find relevant information
- Implementation follows established patterns
- Code quality meets documented standards
- Performance targets are consistently met
- Testing strategies are properly applied

### **Warning Signs**
- Agents asking for information that's in memory files
- Inconsistent implementation patterns
- Performance regressions
- Test coverage gaps
- Standards violations

---

## 🔍 **Troubleshooting Memory Issues**

### **Information Not Found**
If agents can't find needed information:
1. Check if information exists in correct memory file
2. Verify information is current and accurate
3. Consider if information belongs in different memory file
4. Add missing information if needed

### **Conflicting Information**
If memory files contradict each other:
1. Identify which file should be authoritative
2. Update the incorrect information
3. Ensure consistency across all files
4. Add cross-references if needed

### **Outdated Information**
If memory files are out of sync with codebase:
1. Review and update outdated sections
2. Validate against current implementation
3. Test documented examples and commands
4. Update related files for consistency

---

## 🎯 **Memory Usage Examples**

### **Example 1: Implementing New CLI Command**
```
1. Check PM.md for CLI standards and patterns
2. Review engineer.md for Click framework usage
3. Implement following established patterns
4. Use qa.md to create appropriate tests
5. Update engineer.md with any new patterns
```

### **Example 2: Performance Optimization**
```
1. PM.md → Check performance targets (<100ms recall)
2. engineer.md → Review optimization techniques
3. Implement optimizations using documented patterns
4. qa.md → Create benchmark tests
5. Validate against documented performance targets
```

### **Example 3: AI Integration Development**
```
1. PM.md → Understand subprocess-based integration pattern
2. engineer.md → Review AIMemoryIntegration class patterns
3. Implement following universal integration pattern
4. qa.md → Test integration scenarios
5. Update memories with new integration patterns
```

---

**🧠 This memory system enables consistent, high-quality development by providing specialized, role-based knowledge that guides AI agents toward optimal solutions.**