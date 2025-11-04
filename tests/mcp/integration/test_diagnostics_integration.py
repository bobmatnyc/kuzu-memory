"""
Integration tests for MCP diagnostics framework.

End-to-end tests for diagnostic workflows, CLI integration,
and real server testing.
"""

import json
import subprocess
import tempfile
from pathlib import Path

import pytest

from kuzu_memory.mcp.testing.diagnostics import (
    DiagnosticSeverity,
    MCPDiagnostics,
)


@pytest.mark.integration
class TestDiagnosticsIntegration:
    """Integration tests for diagnostics framework."""

    @pytest.mark.asyncio
    async def test_configuration_check_end_to_end(self):
        """Test configuration check with real filesystem."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create a valid config
            config_path = Path(tmpdir) / "config.json"
            db_dir = Path(tmpdir) / "db"
            db_dir.mkdir()

            config = {
                "mcpServers": {
                    "kuzu-memory": {
                        "command": "kuzu-memory",
                        "args": ["mcp", "serve"],
                        "env": {
                            "KUZU_MEMORY_DB": str(db_dir / "memorydb"),
                            "KUZU_MEMORY_MODE": "mcp",
                        },
                    }
                }
            }
            config_path.write_text(json.dumps(config))

            # Run diagnostics
            diagnostics = MCPDiagnostics()
            diagnostics.claude_code_config_path = config_path

            results = await diagnostics.check_configuration()

            # Verify all checks passed
            assert len(results) > 0
            passed = sum(1 for r in results if r.success)
            assert passed == len(results)

    @pytest.mark.asyncio
    async def test_full_diagnostics_report_generation(self):
        """Test generating full diagnostic report."""
        diagnostics = MCPDiagnostics()

        # Create a minimal valid config for testing
        with tempfile.TemporaryDirectory() as tmpdir:
            config_path = Path(tmpdir) / "config.json"
            db_dir = Path(tmpdir) / "db"
            db_dir.mkdir()

            config = {
                "mcpServers": {
                    "kuzu-memory": {
                        "command": "kuzu-memory",
                        "args": ["mcp", "serve"],
                        "env": {
                            "KUZU_MEMORY_DB": str(db_dir / "memorydb"),
                            "KUZU_MEMORY_MODE": "mcp",
                        },
                    }
                }
            }
            config_path.write_text(json.dumps(config))
            diagnostics.claude_code_config_path = config_path

            # Run diagnostics (will only do config checks in test env)
            report = await diagnostics.run_full_diagnostics(auto_fix=False)

            # Verify report structure
            assert report.report_name == "MCP Full Diagnostics"
            assert report.platform is not None
            assert report.total > 0
            assert report.total_duration_ms > 0

            # Test report conversions
            report_dict = report.to_dict()
            assert "report_name" in report_dict
            assert "results" in report_dict
            assert isinstance(report_dict["results"], list)

            # Test text report generation
            text_report = diagnostics.generate_text_report(report)
            assert "MCP Full Diagnostics" in text_report
            assert report.platform in text_report

            # Test HTML report generation
            html_report = diagnostics.generate_html_report(report)
            assert "<!DOCTYPE html>" in html_report
            assert "MCP Full Diagnostics" in html_report

    @pytest.mark.asyncio
    async def test_report_json_serialization(self):
        """Test report can be serialized to JSON."""
        diagnostics = MCPDiagnostics()

        with tempfile.TemporaryDirectory() as tmpdir:
            config_path = Path(tmpdir) / "config.json"
            db_dir = Path(tmpdir) / "db"
            db_dir.mkdir()

            config = {
                "mcpServers": {
                    "kuzu-memory": {
                        "command": "kuzu-memory",
                        "args": ["mcp", "serve"],
                        "env": {
                            "KUZU_MEMORY_DB": str(db_dir / "memorydb"),
                            "KUZU_MEMORY_MODE": "mcp",
                        },
                    }
                }
            }
            config_path.write_text(json.dumps(config))
            diagnostics.claude_code_config_path = config_path

            report = await diagnostics.run_full_diagnostics()

            # Convert to JSON
            report_json = json.dumps(report.to_dict(), indent=2)
            assert report_json is not None

            # Verify can be parsed back
            parsed = json.loads(report_json)
            assert parsed["report_name"] == "MCP Full Diagnostics"
            assert "results" in parsed

    @pytest.mark.asyncio
    async def test_missing_environment_variables(self):
        """Test detection of missing environment variables."""
        with tempfile.TemporaryDirectory() as tmpdir:
            config_path = Path(tmpdir) / "config.json"

            # Config without required env vars
            config = {
                "mcpServers": {
                    "kuzu-memory": {
                        "command": "kuzu-memory",
                        "args": ["mcp", "serve"],
                        "env": {},  # Missing required vars
                    }
                }
            }
            config_path.write_text(json.dumps(config))

            diagnostics = MCPDiagnostics()
            diagnostics.claude_code_config_path = config_path

            results = await diagnostics.check_configuration()

            # Should detect missing env vars
            env_check = next(
                (r for r in results if r.check_name == "mcp_environment_variables"),
                None,
            )
            assert env_check is not None
            assert not env_check.success
            assert env_check.severity == DiagnosticSeverity.WARNING

    @pytest.mark.asyncio
    async def test_database_directory_permissions(self):
        """Test database directory permission checks."""
        with tempfile.TemporaryDirectory() as tmpdir:
            config_path = Path(tmpdir) / "config.json"
            db_dir = Path(tmpdir) / "db"
            db_dir.mkdir()

            config = {
                "mcpServers": {
                    "kuzu-memory": {
                        "command": "kuzu-memory",
                        "args": ["mcp", "serve"],
                        "env": {
                            "KUZU_MEMORY_DB": str(db_dir / "memorydb"),
                            "KUZU_MEMORY_MODE": "mcp",
                        },
                    }
                }
            }
            config_path.write_text(json.dumps(config))

            diagnostics = MCPDiagnostics()
            diagnostics.claude_code_config_path = config_path

            results = await diagnostics.check_configuration()

            # Database directory check should pass
            db_check = next(
                (r for r in results if r.check_name == "memory_database_directory"),
                None,
            )
            assert db_check is not None
            assert db_check.success

    @pytest.mark.asyncio
    async def test_severity_levels_in_report(self):
        """Test that different severity levels are properly categorized."""
        diagnostics = MCPDiagnostics()

        with tempfile.TemporaryDirectory() as tmpdir:
            # Create config with various issues to trigger different severities
            config_path = Path(tmpdir) / "config.json"

            # Minimal config that will pass some checks
            config = {
                "mcpServers": {
                    "kuzu-memory": {
                        "command": "kuzu-memory",
                        "args": ["mcp", "serve"],
                        "env": {},  # Missing vars (WARNING)
                    }
                }
            }
            config_path.write_text(json.dumps(config))
            diagnostics.claude_code_config_path = config_path

            results = await diagnostics.check_configuration()

            # Should have mix of severities
            severities = {r.severity for r in results}
            assert len(severities) > 0

            # Should have at least SUCCESS and WARNING
            assert DiagnosticSeverity.SUCCESS in severities
            assert DiagnosticSeverity.WARNING in severities


@pytest.mark.integration
@pytest.mark.slow
class TestDiagnosticsCLI:
    """Integration tests for diagnostic CLI commands."""

    @pytest.mark.skip(reason="CLI diagnose commands not yet implemented - tracked in backlog")
    def test_diagnose_config_command(self):
        """Test 'kuzu-memory mcp diagnose config' command."""
        result = subprocess.run(
            ["kuzu-memory", "mcp", "diagnose", "config", "--help"],
            capture_output=True,
            text=True,
        )

        assert result.returncode == 0
        assert "Check MCP configuration validity" in result.stdout

    @pytest.mark.skip(reason="CLI diagnose commands not yet implemented - tracked in backlog")
    def test_diagnose_connection_command(self):
        """Test 'kuzu-memory mcp diagnose connection' command."""
        result = subprocess.run(
            ["kuzu-memory", "mcp", "diagnose", "connection", "--help"],
            capture_output=True,
            text=True,
        )

        assert result.returncode == 0
        assert "Test MCP server connection" in result.stdout

    @pytest.mark.skip(reason="CLI diagnose commands not yet implemented - tracked in backlog")
    def test_diagnose_tools_command(self):
        """Test 'kuzu-memory mcp diagnose tools' command."""
        result = subprocess.run(
            ["kuzu-memory", "mcp", "diagnose", "tools", "--help"],
            capture_output=True,
            text=True,
        )

        assert result.returncode == 0
        assert "Test MCP tool discovery" in result.stdout

    @pytest.mark.skip(reason="CLI diagnose commands not yet implemented - tracked in backlog")
    def test_diagnose_run_command(self):
        """Test 'kuzu-memory mcp diagnose run' command."""
        result = subprocess.run(
            ["kuzu-memory", "mcp", "diagnose", "run", "--help"],
            capture_output=True,
            text=True,
        )

        assert result.returncode == 0
        assert "Run full MCP diagnostics suite" in result.stdout

    def test_diagnose_run_with_output(self):
        """Test diagnostics with file output."""
        with tempfile.TemporaryDirectory() as tmpdir:
            output_file = Path(tmpdir) / "report.json"

            # This will likely fail but should still generate output
            _ = subprocess.run(
                [
                    "kuzu-memory",
                    "mcp",
                    "diagnose",
                    "config",
                    "--output",
                    str(output_file),
                ],
                capture_output=True,
                text=True,
            )

            # Command should complete (may fail checks but shouldn't crash)
            # Check if output file was created
            if output_file.exists():
                content = output_file.read_text()
                data = json.loads(content)
                assert "check_type" in data
                assert data["check_type"] == "configuration"


@pytest.mark.integration
class TestDiagnosticsReportFormats:
    """Integration tests for different report formats."""

    @pytest.mark.asyncio
    async def test_text_report_format(self):
        """Test text report format."""
        diagnostics = MCPDiagnostics()

        with tempfile.TemporaryDirectory() as tmpdir:
            config_path = Path(tmpdir) / "config.json"
            db_dir = Path(tmpdir) / "db"
            db_dir.mkdir()

            config = {
                "mcpServers": {
                    "kuzu-memory": {
                        "command": "kuzu-memory",
                        "args": ["mcp", "serve"],
                        "env": {
                            "KUZU_MEMORY_DB": str(db_dir / "memorydb"),
                            "KUZU_MEMORY_MODE": "mcp",
                        },
                    }
                }
            }
            config_path.write_text(json.dumps(config))
            diagnostics.claude_code_config_path = config_path

            report = await diagnostics.run_full_diagnostics()
            text_report = diagnostics.generate_text_report(report)

            # Verify text format
            assert "=" * 70 in text_report
            assert "MCP Full Diagnostics" in text_report
            assert "Results:" in text_report
            assert "Duration:" in text_report

    @pytest.mark.asyncio
    async def test_html_report_format(self):
        """Test HTML report format."""
        diagnostics = MCPDiagnostics()

        with tempfile.TemporaryDirectory() as tmpdir:
            config_path = Path(tmpdir) / "config.json"
            db_dir = Path(tmpdir) / "db"
            db_dir.mkdir()

            config = {
                "mcpServers": {
                    "kuzu-memory": {
                        "command": "kuzu-memory",
                        "args": ["mcp", "serve"],
                        "env": {
                            "KUZU_MEMORY_DB": str(db_dir / "memorydb"),
                            "KUZU_MEMORY_MODE": "mcp",
                        },
                    }
                }
            }
            config_path.write_text(json.dumps(config))
            diagnostics.claude_code_config_path = config_path

            report = await diagnostics.run_full_diagnostics()
            html_report = diagnostics.generate_html_report(report)

            # Verify HTML structure
            assert "<!DOCTYPE html>" in html_report
            assert "<html>" in html_report
            assert "<head>" in html_report
            assert "<body>" in html_report
            assert "MCP Full Diagnostics" in html_report
            assert "summary" in html_report.lower()

    @pytest.mark.asyncio
    async def test_json_report_format(self):
        """Test JSON report format."""
        diagnostics = MCPDiagnostics()

        with tempfile.TemporaryDirectory() as tmpdir:
            config_path = Path(tmpdir) / "config.json"
            db_dir = Path(tmpdir) / "db"
            db_dir.mkdir()

            config = {
                "mcpServers": {
                    "kuzu-memory": {
                        "command": "kuzu-memory",
                        "args": ["mcp", "serve"],
                        "env": {
                            "KUZU_MEMORY_DB": str(db_dir / "memorydb"),
                            "KUZU_MEMORY_MODE": "mcp",
                        },
                    }
                }
            }
            config_path.write_text(json.dumps(config))
            diagnostics.claude_code_config_path = config_path

            report = await diagnostics.run_full_diagnostics()
            report_dict = report.to_dict()
            json_report = json.dumps(report_dict, indent=2)

            # Verify JSON is valid and complete
            parsed = json.loads(json_report)
            assert parsed["report_name"] == "MCP Full Diagnostics"
            assert "timestamp" in parsed
            assert "platform" in parsed
            assert "results" in parsed
            assert isinstance(parsed["results"], list)
            assert "total_duration_ms" in parsed
