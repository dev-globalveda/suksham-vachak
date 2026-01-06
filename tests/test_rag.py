"""Tests for RAG Déjà Vu Engine."""

from suksham_vachak.rag.models import (
    CricketMoment,
    MomentSource,
    MomentType,
    RetrievedMoment,
)


class TestCricketMoment:
    """Tests for CricketMoment dataclass."""

    def test_to_embedding_text_basic(self):
        """Test basic embedding text generation."""
        moment = CricketMoment(
            moment_id="test_1",
            source=MomentSource.CURATED,
            match_id="test_match",
            match_format="T20",
            date="2024-01-01",
            venue="Test Stadium",
            teams=("Team A", "Team B"),
            moment_type=MomentType.WICKET,
            primary_player="Virat Kohli",
            secondary_player="Pat Cummins",
            phase="death",
            pressure_level="critical",
            momentum="batting_dominant",
            score=150,
            wickets=4,
            description="Kohli dismissed by Cummins",
        )

        text = moment.to_embedding_text()

        assert "Virat Kohli" in text
        assert "wicket" in text
        assert "T20" in text
        assert "death phase" in text
        assert "critical pressure" in text
        assert "Pat Cummins" in text

    def test_to_embedding_text_with_chase(self):
        """Test embedding text with chase context."""
        moment = CricketMoment(
            moment_id="test_2",
            source=MomentSource.CRICSHEET,
            match_id="test_match",
            match_format="ODI",
            date="2024-01-01",
            venue="Test Stadium",
            teams=("India", "Australia"),
            moment_type=MomentType.CLUTCH,
            primary_player="MS Dhoni",
            phase="death",
            pressure_level="critical",
            target=275,
            runs_required=15,
            score=260,
            wickets=4,
            description="Dhoni hits winning six",
        )

        text = moment.to_embedding_text()

        assert "chasing 275" in text
        assert "needing 15 runs" in text
        assert "ODI" in text

    def test_to_embedding_text_uses_precomputed(self):
        """Test that precomputed embedding_text is used."""
        moment = CricketMoment(
            moment_id="test_3",
            source=MomentSource.CURATED,
            primary_player="Sachin Tendulkar",
            embedding_text="Custom embedding text for Sachin",
        )

        text = moment.to_embedding_text()

        assert text == "Custom embedding text for Sachin"

    def test_to_metadata(self):
        """Test metadata conversion for ChromaDB."""
        moment = CricketMoment(
            moment_id="test_meta",
            source=MomentSource.CURATED,
            priority=2.5,
            match_id="match_123",
            match_format="T20",
            date="2024-01-01",
            venue="MCG",
            teams=("India", "Pakistan"),
            moment_type=MomentType.CLUTCH,
            primary_player="Kohli",
            secondary_player="Rauf",
            phase="death",
            pressure_level="critical",
            momentum="momentum_shift",
            target=160,
            tags=["t20_wc", "kohli", "chase"],
        )

        metadata = moment.to_metadata()

        assert metadata["moment_id"] == "test_meta"
        assert metadata["source"] == "curated"
        assert metadata["priority"] == 2.5
        assert metadata["match_format"] == "T20"
        assert metadata["team1"] == "India"
        assert metadata["team2"] == "Pakistan"
        assert metadata["primary_player"] == "Kohli"
        assert metadata["tags"] == "t20_wc,kohli,chase"

    def test_from_metadata(self):
        """Test reconstruction from ChromaDB metadata."""
        metadata = {
            "moment_id": "test_from",
            "source": "cricsheet",
            "priority": 0.8,
            "match_id": "match_456",
            "match_format": "ODI",
            "date": "2023-11-19",
            "venue": "Ahmedabad",
            "team1": "India",
            "team2": "Australia",
            "moment_type": "wicket",
            "ball_number": "45.3",
            "innings": 2,
            "primary_player": "Rohit Sharma",
            "secondary_player": "Starc",
            "phase": "middle",
            "pressure_level": "high",
            "momentum": "bowling_dominant",
            "target": 241,
            "tags": "world_cup,final",
        }

        moment = CricketMoment.from_metadata(metadata, "Rohit dismissed by Starc")

        assert moment.moment_id == "test_from"
        assert moment.source == MomentSource.CRICSHEET
        assert moment.match_format == "ODI"
        assert moment.teams == ("India", "Australia")
        assert moment.primary_player == "Rohit Sharma"
        assert moment.description == "Rohit dismissed by Starc"
        assert "world_cup" in moment.tags


class TestRetrievedMoment:
    """Tests for RetrievedMoment dataclass."""

    def test_to_callback_string(self):
        """Test callback string formatting."""
        moment = CricketMoment(
            moment_id="callback_test",
            source=MomentSource.CURATED,
            match_id="wc2011_final",
            match_format="ODI",
            date="2011-04-02",
            venue="Wankhede Stadium",
            teams=("India", "Sri Lanka"),
            moment_type=MomentType.CLUTCH,
            primary_player="MS Dhoni",
            description="Dhoni finishes World Cup final with a six",
        )

        retrieved = RetrievedMoment(moment=moment, similarity_score=0.85)
        callback = retrieved.to_callback_string()

        assert "History:" in callback
        assert "Dhoni finishes World Cup final with a six" in callback
        assert "India vs Sri Lanka" in callback
        assert "2011-04-02" in callback


class TestMomentEnums:
    """Tests for moment enums."""

    def test_moment_type_values(self):
        """Test MomentType enum values."""
        assert MomentType.WICKET.value == "wicket"
        assert MomentType.MILESTONE.value == "milestone"
        assert MomentType.CLUTCH.value == "clutch"
        assert MomentType.ICONIC.value == "iconic"

    def test_moment_source_values(self):
        """Test MomentSource enum values."""
        assert MomentSource.CRICSHEET.value == "cricsheet"
        assert MomentSource.CURATED.value == "curated"
