class SourceError(RuntimeError):
    """소스 API가 오류를 돌려줬다. 재시도해도 같은 결과일 가능성이 높다."""


class DataNotReady(SourceError):
    """요청한 날짜의 데이터가 아직 공개되지 않았다. 나중에 재시도하면 된다."""
