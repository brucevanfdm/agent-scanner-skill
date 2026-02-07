# Copyright 2026 Cisco Systems, Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#
# SPDX-License-Identifier: Apache-2.0

"""
Configuration class for Skill Scanner.
"""

import os
from dataclasses import dataclass
from pathlib import Path


@dataclass
class Config:
    """
    Configuration for Skill Scanner.
    """

    # Analyzer Configuration
    enable_static_analyzer: bool = True
    enable_behavioral_analyzer: bool = False

    # Scanning Options
    max_file_size_mb: int = 10
    scan_timeout_seconds: int = 300

    # Output Options
    output_format: str = "summary"
    detailed_output: bool = False

    def __post_init__(self):
        """Load configuration from environment variables if not provided."""

        # Analyzer toggles from environment
        if os.getenv("ENABLE_STATIC_ANALYZER", "").lower() in ("false", "0"):
            self.enable_static_analyzer = False

        if os.getenv("ENABLE_BEHAVIORAL_ANALYZER", "").lower() in ("true", "1"):
            self.enable_behavioral_analyzer = True

    @classmethod
    def from_env(cls) -> "Config":
        """
        Create configuration from environment variables.

        Returns:
            Config instance with values from environment
        """
        return cls()

    @classmethod
    def from_file(cls, config_file: Path) -> "Config":
        """
        Load configuration from .env file.

        Args:
            config_file: Path to .env file

        Returns:
            Config instance
        """
        # Load .env file
        if config_file.exists():
            with open(config_file) as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith("#") and "=" in line:
                        key, value = line.split("=", 1)
                        os.environ[key.strip()] = value.strip()

        return cls.from_env()
