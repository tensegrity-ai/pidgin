# tests/unit/test_name_generator.py
"""Test experiment name generator."""


from pidgin.cli.name_generator import ADJECTIVES, NOUNS, generate_experiment_name


class TestGenerateExperimentName:
    """Test experiment name generation."""

    def test_basic_generation(self):
        """Test basic name generation."""
        name = generate_experiment_name()

        # Check format
        assert "-" in name
        parts = name.split("-")
        assert len(parts) == 2

        # Check components are from lists
        adjective, noun = parts
        assert adjective in ADJECTIVES
        assert noun in NOUNS

    def test_randomness(self):
        """Test that names are random."""
        names = [generate_experiment_name() for _ in range(10)]

        # Should have some variety (not all the same)
        unique_names = set(names)
        assert len(unique_names) > 1

    def test_seeded_generation(self):
        """Test reproducible generation with seed."""
        seed = "test_seed"

        # Generate with same seed multiple times
        name1 = generate_experiment_name(seed)
        name2 = generate_experiment_name(seed)
        name3 = generate_experiment_name(seed)

        # Should all be the same
        assert name1 == name2 == name3

        # Different seed should give different name
        name4 = generate_experiment_name("different_seed")
        assert name4 != name1

    def test_format_consistency(self):
        """Test name format consistency."""
        for _ in range(20):
            name = generate_experiment_name()

            # Always lowercase
            assert name.islower()

            # Always hyphenated
            assert name.count("-") == 1

            # No spaces or special characters
            assert all(c.isalpha() or c == "-" for c in name)

    def test_all_components_accessible(self):
        """Test that all adjectives and nouns can be selected."""
        # Use different seeds to get variety
        names = []
        for i in range(100):
            names.append(generate_experiment_name(str(i)))

        # Extract components
        adjectives_used = set()
        nouns_used = set()

        for name in names:
            adj, noun = name.split("-")
            adjectives_used.add(adj)
            nouns_used.add(noun)

        # Should use a good portion of the available words
        # (not all due to randomness, but a significant portion)
        assert len(adjectives_used) >= min(10, len(ADJECTIVES) // 2)
        assert len(nouns_used) >= min(10, len(NOUNS) // 2)
