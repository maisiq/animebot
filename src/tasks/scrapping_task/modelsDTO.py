from pydantic import BaseModel


class AnimeEpisode(BaseModel):
    title_ru: str
    episode_number: int
    studio_name: str

    def __hash__(self) -> int:
        return hash(repr(self))

    def __eq__(self, other):
        return repr(self) == repr(other)

    def __repr__(self):
        return '&&'.join([self.title_ru, str(self.episode_number), self.studio_name])

    def __str__(self):
        return f'{self.title_ru} ({self.studio_name}), {self.episode_number} серия'

    @classmethod
    def from_str(cls, string: str):
        title_ru, episode_number, studio_name = string.split('&&')
        return cls(title_ru=title_ru, episode_number=int(episode_number), studio_name=studio_name)
