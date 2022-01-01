import praw


class CustomRedditClient(praw.Reddit):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def _to_dict(self, obj):
        j = {k: v for k, v in obj.__dict__.items() if k != '_reddit'}
        if isinstance(obj, praw.models.reddit.submission.Submission):  # type: ignore
            if j["subreddit"] is not None:
                j["subreddit"] = str(j['subreddit'])
            if j['author'] is not None:
                j["author"] = str(j["author"])
        return j

    def info(self, list_of_subs):
        return [self._to_dict(x) for x in super().info(list_of_subs) if x is not None]
