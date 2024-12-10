from dataclasses import dataclass


@dataclass
class FileModel:
    file_name: str
    file_size: int
    file_path: str
    
    @staticmethod
    def format_file_size(size: int) -> str:
        """Formata o tamanho do arquivo em KB/MB."""
        if size < 1024:
            return f"{size} bytes"
        elif size < 1024 ** 2:
            return f"{size / 1024:.2f} KB"
        else:
            return f"{size / (1024 ** 2):.2f} MB"