from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton


def get_source_keyboard(original_url: str) -> InlineKeyboardMarkup:
    """Creates inline keyboard with a button linking to original video source."""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="🔗 Original Source",
                    url=original_url
                )
            ]
        ]
    )
