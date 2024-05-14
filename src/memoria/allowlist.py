import re
from logging import getLogger
from dataclasses import dataclass, field
from enum import Enum, auto
from ipaddress import AddressValueError, IPv4Address
from shlex import split as shlex_split
from typing import Iterator, TYPE_CHECKING
from urllib.parse import ParseResult

if TYPE_CHECKING:
    from io import TextIOBase
    from aiofiles.threadpool.text import AsyncTextIOWrapper

# from logging import getLogger


_LOG = getLogger(__spec__.name)


class AllowlistDecision(Enum):
    Allow = auto()
    Deny = auto()
    HardAllow = auto()
    HardDeny = auto()

    def __bool__(self) -> bool:
        return self in (AllowlistDecision.Allow, AllowlistDecision.HardAllow)


@dataclass
class AllowlistEntry:
    host: str

    allow: bool

    paths: list[str] = field(default_factory=list)

    def _paths_str(self) -> str:
        if not self.paths:
            return ''

        return "[" + ' | '.join(x for x in self.paths if x[0] == '/') + "]"

    def __str__(self) -> str:
        return f"[*.]{self.host}{self._paths_str() if self.paths else '[*]'}: `{'`, `'.join(x for x in self.paths if x[0] != '/')}`"

    def _check_rule(self, unparse: str, uri: ParseResult, rule: str) -> bool:
        if rule.startswith('/'):
            # Path prefix
            if uri.path.startswith(rule):
                return True
        elif rule.startswith('r'):
            return any(True for _ in re.findall(rule[1:], unparse))
        else:
            raise NotImplementedError(f"Don't know how to handle rule: {rule}")
        return False

    def check(self, unparse: str, uri: ParseResult) -> AllowlistDecision | None:
        if self.paths:
            if any(self._check_rule(unparse, uri, p) for p in self.paths):
                return AllowlistDecision.HardAllow if self.allow else AllowlistDecision.HardDeny
            return None
        return AllowlistDecision.Allow if self.allow else AllowlistDecision.Deny

    @staticmethod
    def from_file(allow: bool, line: str) -> 'AllowlistEntry':
        host, *parts = shlex_split(line)
        return AllowlistEntry(host, allow, paths=parts)

    @staticmethod
    def _escape_path(path: str) -> str:
        ret = path.replace('"', '\\"').replace("'", "\\'")
        if ' ' in ret:
            return f'"{ret}"'
        return ret

    def dumps(self) -> str:
        if not self.paths:
            return self.host
        return self.host + ' ' + ' '.join(self.paths)

    @classmethod
    def load_acls(cls, acls: dict[str, list['AllowlistEntry']], file: 'TextIOBase', allow: bool) -> None:
        for line in file:
            if line.isspace():
                continue
            entry = cls.from_file(allow, line)
            if entry.host not in acls:
                acls[entry.host] = [entry]
            else:
                acls[entry.host].append(entry)
            _LOG.debug(f"Loaded {'allow' if allow else 'deny'}list entry: {entry}...")

    @classmethod
    async def load_acls_async(cls, acls: dict[str, list['AllowlistEntry']], file: 'AsyncTextIOWrapper', allow: bool) -> None:
        async for line in file:
            if line.isspace():
                continue
            entry = cls.from_file(allow, line)
            if entry.host not in acls:
                acls[entry.host] = [entry]
            else:
                acls[entry.host].append(entry)
            _LOG.debug(f"Loaded {'allow' if allow else 'deny'}list entry: {entry}...")

    @staticmethod
    def _check_hostname_acls(unparse: str, parse: ParseResult, acls: list['AllowlistEntry']) -> Iterator[AllowlistDecision]:
        for acl in acls:
            decision = acl.check(unparse, parse)
            if decision is None:
                continue

            if decision in (AllowlistDecision.HardAllow, AllowlistDecision.HardDeny):
                yield decision
                return

            yield decision

    @staticmethod
    def check_parse_acls(unparse: str, parse: ParseResult, acls: dict[str, list['AllowlistEntry']]) -> bool | None:
        if parse.hostname is None:
            return False

        # Special handling for IPv4...
        current_decision: AllowlistDecision | None = None
        try:
            IPv4Address(parse.hostname)
            hostname = parse.netloc
            current_decision_hostname: str = hostname
            if parse.netloc not in acls:
                return False

            for decision in AllowlistEntry._check_hostname_acls(unparse, parse, acls[hostname]):
                match current_decision, decision:
                    case (AllowlistDecision.Allow, AllowlistDecision.Deny) | (AllowlistDecision.Deny, AllowlistDecision.Allow) if hostname == current_decision_hostname:
                        raise RuntimeError(f"Same site ({hostname}) in both allow and deny lists!")

                    case _, (AllowlistDecision.HardAllow | AllowlistDecision.HardDeny):
                        return bool(current_decision)

                    case None, _:
                        current_decision = decision
                        current_decision_hostname = hostname
            if current_decision is None:
                return None
            return bool(current_decision)
        except AddressValueError:
            pass

        hostname = parse.netloc
        current_decision_hostname: str = hostname

        while current_decision not in (AllowlistDecision.HardAllow, AllowlistDecision.HardDeny):
            for decision in AllowlistEntry._check_hostname_acls(unparse, parse, acls.get(hostname, [])):
                match current_decision, decision:
                    case (AllowlistDecision.Allow, AllowlistDecision.Deny) | (AllowlistDecision.Deny, AllowlistDecision.Allow) if hostname == current_decision_hostname:
                        raise RuntimeError(
                            f"Same site ({', '.join({current_decision_hostname, hostname})}) in both allow and deny lists!")

                    case _, (AllowlistDecision.HardAllow | AllowlistDecision.HardDeny):
                        return bool(decision)

                    case None, _:
                        current_decision = decision
                        current_decision_hostname = hostname
                        continue

                    # case _, _:
                    # input(f"{current_decision=} ({current_decision_hostname}), {decision=} ({hostname})")

            if '.' not in hostname:
                break
            hostname = '.'.join(hostname.split('.')[1:])

        if current_decision is None:
            return None

        return bool(current_decision)
