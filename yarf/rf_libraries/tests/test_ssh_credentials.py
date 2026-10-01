import inspect
from pathlib import Path
from textwrap import dedent
from unittest.mock import MagicMock, patch

import pytest
from robot.utils import normalize
from SSHLibrary import SSHLibrary

from yarf.errors.yarf_errors import YARFCredentialError, YARFExitCode
from yarf.rf_libraries.ssh_credentials import (
    LOGIN_KEYWORD_PARAMS,
    check_ssh_credentials,
)

CLI_VARIABLES = ["SSH_USER:ubuntu", "SSH_PASSWORD:secret", "SSH_KEY:id"]


def write_suite(suite_dir: Path, files: dict[str, str]) -> None:
    """
    Write suite files into a directory.

    Args:
        suite_dir: The suite directory.
        files: Relative file paths and their content.
    """
    for name, content in files.items():
        path = suite_dir / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(dedent(content))


class TestCheckSSHCredentials:
    @pytest.mark.parametrize("name,params", LOGIN_KEYWORD_PARAMS.items())
    def test_login_keyword_params(
        self, name: str, params: tuple[str, ...]
    ) -> None:
        """
        Test that the login keyword parameters match the installed SSHLibrary.
        """
        method = {
            normalize(m, ignore="_"): getattr(SSHLibrary, m)
            for m in ("login", "login_with_public_key")
        }[name]
        assert tuple(inspect.signature(method).parameters)[1:] == params

    @pytest.mark.parametrize(
        "body",
        [
            "Login    ${SSH_USER}    ${SSH_PASSWORD}    delay=1s",
            "Login    username=${ssh user}    password=${SSH_PASSWORD}",
            "SSHLibrary.Login With Public Key    ${SSH_USER}    ${SSH_KEY}",
            "Login With Public Key    ${SSH_USER}    ${SSH_KEY}    "
            "password=${SSH_PASSWORD}",
            "Login    read_config=True",
            "Login    ${SSH_USER}    ${SSH_PASSWORD}"
            + "    x" * (len(LOGIN_KEYWORD_PARAMS["login"]) - 1),
            "Open Connection    localhost",
            "Other.Login    admin    admin",
        ],
    )
    def test_cli_credentials(self, tmp_path: Path, body: str) -> None:
        """
        Test that login keywords taking credentials from command line
        variables, and other keywords, are accepted.
        """
        write_suite(
            tmp_path,
            {
                "suite.robot": f"""
                *** Settings ***
                Library    SSHLibrary

                *** Test Cases ***
                Test
                    {body}
                """,
                "image.png": "",
            },
        )
        check_ssh_credentials(tmp_path, CLI_VARIABLES)

    def test_no_ssh_library(self, tmp_path: Path) -> None:
        """
        Test that a Login keyword is not checked when SSHLibrary is not
        imported.
        """
        write_suite(
            tmp_path,
            {
                "suite.robot": """
                *** Test Cases ***
                Test
                    Login    admin    admin
                """,
            },
        )
        check_ssh_credentials(tmp_path, [])

    @pytest.mark.parametrize(
        "arg",
        [
            "ubuntu",
            "user=ubuntu",
            "${OTHER}",
            "${SSH_USER}suffix",
            "@{SSH_USER}",
            "${SSH_USER}[0]",
            "%{SSH_USER}",
        ],
    )
    def test_invalid_credential(self, tmp_path: Path, arg: str) -> None:
        """
        Test that a credential that is not only a command line variable is
        rejected.
        """
        write_suite(
            tmp_path,
            {
                "suite.robot": f"""
                *** Settings ***
                Library    SSHLibrary

                *** Test Cases ***
                Test
                    Login    {arg}    ${{SSH_PASSWORD}}
                """,
            },
        )
        with pytest.raises(YARFCredentialError) as exc_info:
            check_ssh_credentials(tmp_path, CLI_VARIABLES)

        assert "suite.robot:7: 'Login' argument 'username'" in str(
            exc_info.value
        )
        assert exc_info.value.exit_code == YARFExitCode.CREDENTIAL_ERROR

    @patch("yarf.rf_libraries.ssh_credentials._owasp_logger")
    def test_hardcoded_credentials(
        self, mock_owasp_logger: MagicMock, tmp_path: Path
    ) -> None:
        """
        Test that hardcoded credentials in settings, aliased imports and
        resource files are all reported, without their values.
        """
        write_suite(
            tmp_path,
            {
                "suite.robot": """
                *** Settings ***
                Library    SSHLibrary    AS    ssh
                Resource    keywords/common.resource
                Suite Setup    Login    ubuntu    ${SSH_PASSWORD}

                *** Test Cases ***
                Test
                    ssh.Login With Public Key    ${SSH_USER}    keyfile=id_rsa
                """,
                "keywords/common.resource": """
                *** Keywords ***
                Connect
                    [Arguments]    ${pw}
                    SSHLibrary.Login    ${SSH_USER}    ${pw}
                """,
            },
        )
        with pytest.raises(YARFCredentialError) as exc_info:
            check_ssh_credentials(tmp_path, CLI_VARIABLES)

        message = str(exc_info.value)
        assert "keywords/common.resource:5: 'SSHLibrary.Login' argument " in (
            message
        )
        assert "suite.robot:5: 'Login' argument 'username'" in message
        assert (
            "suite.robot:9: 'ssh.Login With Public Key' argument 'keyfile'"
            in message
        )
        assert "ubuntu" not in message
        assert "id_rsa" not in message
        mock_owasp_logger.input_validation_fail.assert_called_once()
        assert mock_owasp_logger.input_validation_fail.call_args.args[0] == [
            "keyfile",
            "password",
            "username",
        ]
