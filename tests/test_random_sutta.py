import pytest

from little_bits_of_buddha_worldofgeese.data import random_sutta

SUTTAS = {
    "collection": {
        "MN": {
            "27": {
                "link": "https://www.dhammatalks.org/suttas/MN/MN27.html",
                "quote": "Abandoning divisive speech he abstains from divisive speech. What he has heard here he does not tell there to break those people apart from these people here. What he has heard there he does not tell here to break these people apart from those people there. Thus reconciling those who have broken apart or cementing those who are united, he loves concord, delights in concord, enjoys concord, speaks things that create concord.",
            },
        },
    }
}


@pytest.mark.parametrize(
    "expected_sutta",
    [
        (
            {
                "link": "https://www.dhammatalks.org/suttas/MN/MN27.html",
                "quote": "Abandoning divisive speech he abstains from divisive speech. What he has heard here he does not tell there to break those people apart from these people here. What he has heard there he does not tell here to break these people apart from those people there. Thus reconciling those who have broken apart or cementing those who are united, he loves concord, delights in concord, enjoys concord, speaks things that create concord.",
            }
        ),
    ],
)
def test_sutta(expected_sutta):

    assert random_sutta(suttas=SUTTAS) == expected_sutta
