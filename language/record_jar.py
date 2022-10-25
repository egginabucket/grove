"""
https://datatracker.ietf.org/doc/pdf/draft-phillips-record-jar-02
used for parsing the IANA language subtag registry
https://www.iana.org/assignments/language-subtag-registry/language-subtag-registry
"""


from typing import Any, Iterable, Generator


class Record(dict[str, list[str]]):
    def add(self, key: str, val: str):
        """
        Adds a value to a field.
        """
        if key in self:
            self[key].append(val)
        else:
            self[key] = [val]

    def one(self, key: str) -> str:
        """
        Return a single value from a field.

        Raises
        ------
        ValueError
            If the field has multiple values.
        KeyError
            If the field has no values.
        """
        vals = self[key]
        if len(vals) > 1:
            raise ValueError(f"key '{key}' has multiple values {vals}")
        if not vals:
            raise KeyError(f"key '{key}' has an empty list of values")
        return vals[0]

    def get_one(self, key: str, default=None) -> str | None | Any:
        """
        Return a single value from a field, or `default`.

        Raises
        ------
        ValueError
            If the field has multiple values.
        """
        try:
            return self.one(key)
        except KeyError:
            return default


def parse_record_jar(lines: Iterable[str], indent='\t') -> Generator[Record, None, None]:
    """
    Yields records from an iterable of lines.
    """
    record = Record()
    for line in lines:
        line_text = line.strip()
        if not line_text:
            continue
        if line.startswith(indent):
            record[key][-1] += ' ' + line_text
        elif line_text == '%%':
            yield record
            record = Record()
        else:
            key, val = line_text.split(":", 1)
            record.add(key.strip(), val.strip())
    yield record
