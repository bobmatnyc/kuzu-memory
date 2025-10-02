#!/usr/bin/env node
/**
 * JavaScript/Node.js Integration Example for KuzuMemory
 *
 * This module demonstrates how to integrate KuzuMemory with JavaScript AI applications.
 * Uses child_process.spawn for reliable CLI integration.
 */

const { spawn } = require('child_process');
const path = require('path');

class KuzuMemoryIntegration {
    /**
     * Initialize KuzuMemory integration.
     *
     * @param {string} projectPath - Path to project root (auto-detected if null)
     * @param {number} timeout - Timeout for CLI operations in milliseconds
     */
    constructor(projectPath = null, timeout = 5000) {
        this.projectPath = projectPath || process.cwd();
        this.timeout = timeout;
    }

    /**
     * Enhance a prompt with relevant memory context.
     *
     * @param {string} prompt - Original prompt to enhance
     * @param {string} format - Output format ('plain', 'context', 'json')
     * @param {number} maxMemories - Maximum memories to include
     * @returns {Promise<string>} Enhanced prompt with context
     */
    async enhancePrompt(prompt, format = 'plain', maxMemories = 5) {
        try {
            const args = [
                'enhance', prompt,
                '--format', format,
                '--max-memories', maxMemories.toString(),
                '--project-root', this.projectPath
            ];

            const result = await this._runCommand('kuzu-memory', args);
            return result.trim();

        } catch (error) {
            console.warn(`Enhancement failed: ${error.message}`);
            return prompt;
        }
    }

    /**
     * Store learning content asynchronously (non-blocking).
     *
     * @param {string} content - Content to learn from
     * @param {string} source - Source identifier
     * @param {boolean} quiet - Suppress output (recommended for AI workflows)
     * @param {Object} metadata - Additional metadata
     * @returns {Promise<boolean>} True if learning was queued successfully
     */
    async storeLearning(content, source = 'ai-conversation', quiet = true, metadata = null) {
        try {
            const args = [
                'learn', content,
                '--source', source,
                '--project-root', this.projectPath
            ];

            if (quiet) {
                args.push('--quiet');
            }

            if (metadata) {
                args.push('--metadata', JSON.stringify(metadata));
            }

            // Fire and forget - don't wait for completion
            this._runCommand('kuzu-memory', args, false);
            return true;

        } catch (error) {
            console.warn(`Learning failed: ${error.message}`);
            return false;
        }
    }

    /**
     * Get project memory statistics.
     *
     * @returns {Promise<Object>} Project statistics object
     */
    async getProjectStats() {
        try {
            const args = [
                'stats',
                '--format', 'json',
                '--project-root', this.projectPath
            ];

            const result = await this._runCommand('kuzu-memory', args);
            return JSON.parse(result);

        } catch (error) {
            console.warn(`Stats retrieval failed: ${error.message}`);
            return {};
        }
    }

    /**
     * Run a command using child_process.spawn.
     *
     * @param {string} command - Command to run
     * @param {Array<string>} args - Command arguments
     * @param {boolean} wait - Whether to wait for completion
     * @returns {Promise<string>} Command output
     * @private
     */
    _runCommand(command, args, wait = true) {
        return new Promise((resolve, reject) => {
            const child = spawn(command, args);

            let stdout = '';
            let stderr = '';

            child.stdout.on('data', (data) => {
                stdout += data.toString();
            });

            child.stderr.on('data', (data) => {
                stderr += data.toString();
            });

            if (!wait) {
                resolve(''); // For fire-and-forget operations
                return;
            }

            const timer = setTimeout(() => {
                child.kill();
                reject(new Error(`Command timed out after ${this.timeout}ms`));
            }, this.timeout);

            child.on('close', (code) => {
                clearTimeout(timer);

                if (code === 0) {
                    resolve(stdout);
                } else {
                    reject(new Error(`Command failed with code ${code}: ${stderr}`));
                }
            });

            child.on('error', (error) => {
                clearTimeout(timer);
                reject(error);
            });
        });
    }
}

/**
 * Example of AI conversation enhanced with memory.
 *
 * @param {string} userInput - User's input/question
 * @param {KuzuMemoryIntegration} memory - KuzuMemory integration instance
 * @returns {Promise<string>} AI response
 */
async function aiConversationWithMemory(userInput, memory) {
    // Enhance prompt with memory context
    const enhancedPrompt = await memory.enhancePrompt(userInput);

    // Send enhanced prompt to your AI system
    const aiResponse = await yourAISystem(enhancedPrompt);

    // Store the learning asynchronously (non-blocking)
    const learningContent = `User asked: ${userInput}\nAI responded: ${aiResponse}`;
    await memory.storeLearning(learningContent, 'conversation');

    return aiResponse;
}

/**
 * Placeholder for your AI system integration.
 * Replace with actual AI model calls (OpenAI, Anthropic, etc.)
 *
 * @param {string} prompt - Enhanced prompt
 * @returns {Promise<string>} AI response
 */
async function yourAISystem(prompt) {
    return `AI response to: ${prompt}`;
}

/**
 * Example usage of KuzuMemory integration.
 */
async function main() {
    console.log('KuzuMemory JavaScript Integration Example');

    // Initialize memory integration
    const memory = new KuzuMemoryIntegration();

    // Example conversation
    const questions = [
        "How do I structure an API endpoint?",
        "What's the best way to handle database connections?",
        "How should I write tests for this project?"
    ];

    for (const question of questions) {
        console.log(`\nUser: ${question}`);
        const response = await aiConversationWithMemory(question, memory);
        console.log(`AI: ${response}`);
    }

    // Show project statistics
    console.log('\nProject Memory Statistics:');
    const stats = await memory.getProjectStats();
    console.log(JSON.stringify(stats, null, 2));
}

// Run main function if this file is executed directly
if (require.main === module) {
    main().catch(console.error);
}

module.exports = { KuzuMemoryIntegration, aiConversationWithMemory };
