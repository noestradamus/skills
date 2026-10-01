import pickle
import random
import copy

import numpy as np
import pytest

from neuroevolution_lab.structural import (
    StructuralEngine, ModularNASEngine, architecture_parameters, decode_cppn,
    substrate_coordinates, train_architecture, CanonicalReproduction, CanonicalGenome,
)


class Context:
    def __init__(self):
        self.evaluations = []; self.events = []

    def evaluate(self, genome, fn, label=""):
        result = fn(); assert np.isfinite(result["fitness"])
        self.evaluations.append((genome, result)); return result

    def record(self, event):
        self.events.append(event)


class ConstantCPPN:
    def activate(self, inputs):
        assert len(inputs) == 5
        return [np.arctanh(.6)]


def test_decoder_matches_hand_calculated_expression_and_scales_substrate():
    # tanh(output)=.6, threshold=.2 -> expressed weight=(.6-.2)/.8*3=1.5.
    weights = decode_cppn(ConstantCPPN(), 2, 3, 1, threshold=.2, weight_scale=3.)
    assert len(weights) == 3*3 + 4
    np.testing.assert_allclose(weights, 1.5)
    larger = decode_cppn(ConstantCPPN(), 2, 8, 1)
    assert len(larger) > len(weights)
    np.testing.assert_allclose(larger, 1.5)
    np.testing.assert_array_equal(substrate_coordinates(1, 0.), [[0., 0.]])

def test_hyperneat_queries_bias_coordinates_distance_sign_and_suppression():
    class CoordinateCPPN:
        def __init__(self): self.queries=[]
        def activate(self,q):
            self.queries.append(list(q))
            return [np.arctanh(.4*q[0]+.1*q[2]+.08*q[1])]
    cppn=CoordinateCPPN()
    weights=decode_cppn(cppn,2,2,1,threshold=.2,weight_scale=4.)
    expected_queries=[[-1,-1,-1,0,1],[-1,-1,1,0,np.sqrt(5)],
                      [1,-1,-1,0,np.sqrt(5)],[1,-1,1,0,1],
                      [0,-1.25,-1,0,np.sqrt(41)/4],[0,-1.25,1,0,np.sqrt(41)/4],
                      [-1,0,0,1,np.sqrt(2)],[1,0,0,1,np.sqrt(2)],[0,-.25,0,1,1.25]]
    np.testing.assert_allclose(cppn.queries,expected_queries,atol=1e-12)
    # Hand-derived expression values -.58,-.38,.22,.42,-.2,0,-.4,.4,-.02.
    np.testing.assert_allclose(weights,[-1.9,-.9,.1,1.1,0,0,-1,1,0],atol=1e-12)


@pytest.mark.parametrize("method", ["neat", "cppn", "hyperneat"])
def test_structural_evolution_replay_and_global_rng_isolation(method):
    ambient = random.getstate()
    engine = StructuralEngine({"method": method, "seed": 13, "population_size": 6, "generations": 2})
    assert random.getstate() == ambient
    context = Context(); engine.step(context)
    assert random.getstate() == ambient
    resumed = pickle.loads(pickle.dumps(engine))
    engine.step(context); resumed.step(Context())
    assert engine.summary() == resumed.summary()
    assert random.getstate() == ambient
    assert engine.replay() == engine.best_result
    assert len(context.evaluations) == 12
    assert engine.config.reproduction_config.fitness_sharing == "canonical"
    assert engine.config.reproduction_config.spawn_method == "proportional"
    assert engine.config.genome_config.num_hidden == 0
    connections = engine.summary()["best_genome"]["connections"]
    assert all(isinstance(connection["innovation"], int) for connection in connections)
    assert context.events[-1]["ancestors"]


def test_neat_structural_mutation_really_adds_nodes_and_preserves_innovations():
    engine = StructuralEngine({"method": "neat", "seed": 3, "population_size": 6, "generations": 2})
    engine.config.genome_config.node_add_prob = 1.
    engine.config.genome_config.conn_add_prob = 0.
    context = Context(); engine.step(context); engine.step(context)
    assert max(item["nodes"] for item in context.events[-1]["evaluated"]) > 1


@pytest.mark.parametrize("method", ["neat", "cppn", "hyperneat"])
def test_evolution_profile_identity_follows_checkpoint_genome_type(method):
    import neat
    engine = StructuralEngine({"method": method, "population_size": 3, "generations": 1})
    assert engine.summary()["evolution_profile"] == "paper-profile-v2"
    assert engine.summary()["evolution_backend"] == "canonical_neat_python"
    # Old pickles retain DefaultGenome; loading must not falsely upgrade their
    # algorithm identity merely because today's StructuralEngine class is newer.
    legacy = copy.deepcopy(engine)
    legacy.config.genome_type = neat.DefaultGenome
    restored = pickle.loads(pickle.dumps(legacy))
    assert restored.summary()["evolution_profile"] == "legacy"
    assert restored.summary()["evolution_backend"] == "legacy_neat_python"


def test_neat_speciation_separates_incompatible_genomes():
    engine = StructuralEngine({"method": "neat", "seed": 9, "population_size": 6, "generations": 1})
    engine.config.species_set_config.compatibility_threshold = .1
    engine.population.species.speciate(engine.config, engine.population.population, 0)
    assert len(engine.population.species.species) > 1
    assert set(engine.population.species.genome_to_species) == set(engine.population.population)
    genomes = list(engine.population.population.values())
    shared = set(genomes[0].connections) & set(genomes[1].connections)
    assert shared
    assert all(genomes[0].connections[key].innovation == genomes[1].connections[key].innovation for key in shared)


def _two_species_engine(sharing="canonical", interspecies=0.):
    from neat.species import Species
    engine = StructuralEngine({"method": "neat", "seed": 2, "population_size": 12, "generations": 1})
    genomes = list(engine.population.population.values())
    species_set = engine.population.species
    species_set.species = {}; species_set.genome_to_species = {}
    membership = {}
    for sid, members, fitness in [(1, genomes[:2], 2.), (2, genomes[2:], 6.)]:
        species = Species(sid, 0); species.update(members[0], {g.key: g for g in members})
        for genome in members:
            genome.fitness = fitness
            species_set.genome_to_species[genome.key] = sid; membership[genome.key] = sid
        species_set.species[sid] = species
    engine.config.reproduction_config.fitness_sharing = sharing
    engine.config.reproduction_config.interspecies_crossover_prob = interspecies
    return engine, membership


def test_canonical_sharing_and_species_spawn_against_independent_expected_counts():
    import neat
    for sharing, expected_counts, expected_sharing in [("canonical", {1: 3, 2: 9}, [2., 6.]),
                                                       ("normalized", {1: 1, 2: 11}, [0., 1.])]:
        engine, membership = _two_species_engine(sharing)
        # Independently: means 2 and 6, not sums 4 and 60, allocate 3/9 of 12.
        assert neat.DefaultReproduction.compute_spawn_proportional([2., 6.], 12, 1) == [3, 9]
        ambient = random.getstate()
        try:
            random.setstate(engine.random_state)
            children = engine.population.reproduction.reproduce(engine.config, engine.population.species, 12, 0)
        finally:
            random.setstate(ambient)
        counts = {1: 0, 2: 0}
        for key in children:
            origin = membership[key] if key in membership else membership[engine.population.reproduction.ancestors[key][0]]
            counts[origin] += 1
        assert counts == expected_counts
        assert [s.adjusted_fitness for s in engine.population.species.species.values()] == expected_sharing


def test_aligned_crossover_uses_innovation_identity_not_dictionary_order(monkeypatch):
    import neat
    from neat.genes import DefaultConnectionGene
    engine = StructuralEngine({"method": "neat", "seed": 4, "population_size": 3, "generations": 1})
    strong, weak = [copy.deepcopy(g) for g in list(engine.population.population.values())[:2]]
    strong.fitness = 2.; weak.fitness = 1.
    weak.connections = dict(reversed(list(weak.connections.items())))
    for connection in strong.connections.values(): connection.weight = 100.+connection.innovation
    for connection in weak.connections.values(): connection.weight = 200.+connection.innovation
    for genome, hidden_id, innovation in [(strong, 98, 901), (weak, 99, 902)]:
        node = copy.deepcopy(genome.nodes[0]); node.key = hidden_id; genome.nodes[hidden_id] = node
        connection = DefaultConnectionGene((-1, hidden_id), innovation=innovation)
        connection.weight = 3.; connection.enabled = True; genome.connections[connection.key] = connection
    monkeypatch.setattr("neat.genes.random", lambda: .1)  # inherit weak values at homologous genes
    child = engine.config.genome_type(1000)
    child.configure_crossover(strong, weak, engine.config.genome_config)
    for key in set(strong.connections) & set(weak.connections):
        assert child.connections[key].innovation == strong.connections[key].innovation
        assert child.connections[key].weight == weak.connections[key].weight
    assert (-1, 98) in child.connections  # fitter parent's disjoint gene
    assert (-1, 99) not in child.connections


def _fixture_genome(engine, key, connections, fitness=1.):
    """Explicit edge/innovation/weight tuples, independent of mutation code."""
    from neat.genes import DefaultConnectionGene
    genome = CanonicalGenome(key)
    template = next(iter(engine.population.population.values())).nodes[0]
    node_ids = set(engine.config.genome_config.output_keys)
    for source, target, innovation, weight, enabled in connections:
        gene = DefaultConnectionGene((source, target), innovation=innovation)
        gene.weight = weight; gene.enabled = enabled
        genome.connections[gene.key] = gene
        node_ids.update(node for node in (source, target) if node >= 0)
    for node_id in node_ids:
        node = copy.deepcopy(template); node.key = node_id; genome.nodes[node_id] = node
    genome.fitness = fitness
    return genome


def test_canonical_distance_matches_book_equation_on_unequal_topologies():
    engine = StructuralEngine({"method": "neat", "population_size": 3, "generations": 1})
    config = engine.config.genome_config
    first = _fixture_genome(engine, 1, [(-1, 0, 1, 0., True)])
    second = _fixture_genome(engine, 2, [(-1, 0, 1, 10., True), (-2, 0, 2, 0., True)])
    # Book Eq 3.1: E=1, D=0, N=2, mean matching difference=10.
    # Upstream returns 2.5 by dividing the weight term by N; this flips the
    # configured threshold-3 compatibility decision. Canonical distance is 4.5.
    assert first.distance(second, config) == pytest.approx(.5 + .4*10)
    assert second.distance(first, config) == first.distance(second, config)
    assert first.distance(second, config) > engine.config.species_set_config.compatibility_threshold

    # Heterogeneous lengths, disjoint AND excess genes, disabled matching genes.
    # Matching innovations 1 and 3 have differences 2 and 6 (mean 4).
    # D=2 (innovations 2 and 4); E=1 (innovation 5); N=4, not the optional N=1.
    first = _fixture_genome(engine, 1, [(-1, 0, 1, 0., False), (-1, 10, 2, 7., True),
                                       (-2, 0, 3, 1., True), (10, 0, 5, 4., True)])
    second = _fixture_genome(engine, 2, [(-1, 0, 1, 2., True), (-2, 0, 3, 7., True),
                                        (-2, 11, 4, 9., False)])
    config.compatibility_excess_coefficient = "2.0"
    config.compatibility_disjoint_coefficient = 3.
    assert first.distance(second, config) == pytest.approx((2*1 + 3*2)/4 + .4*4)
    # Bias, response, activation and enabled-state differences are not Eq 3.1 terms.
    same_connections = copy.deepcopy(first)
    same_connections.nodes[0].bias += 100
    same_connections.nodes[0].response += 2
    same_connections.nodes[0].activation = "gauss"
    for gene in same_connections.connections.values(): gene.enabled = not gene.enabled
    assert first.distance(same_connections, config) == 0.
    empty = _fixture_genome(engine, 3, [])
    assert empty.distance(empty, config) == 0.
    assert first.distance(empty, config) == 2.  # all four genes are excess
    config.compatibility_include_node_genes = True
    with pytest.raises(ValueError, match="excludes node-gene"):
        first.distance(second, config)
    config.compatibility_include_node_genes = False
    config.compatibility_enable_penalty = 1.
    with pytest.raises(ValueError, match="enable-state"):
        first.distance(second, config)


def test_equal_fitness_crossover_can_inherit_both_parents_unmatched_genes(monkeypatch):
    engine = StructuralEngine({"method": "neat", "population_size": 3, "generations": 1})
    config = engine.config.genome_config
    first = _fixture_genome(engine, 1, [(-1, 0, 1, 1., False), (-1, 10, 2, 2., True),
                                       (10, 0, 3, 3., True)])
    second = _fixture_genome(engine, 2, [(-1, 0, 1, 4., False), (-2, 11, 4, 5., True),
                                        (11, 0, 5, 6., True)])
    monkeypatch.setattr("neuroevolution_lab.structural.random.random", lambda: .25)
    monkeypatch.setattr("neuroevolution_lab.structural.random.shuffle", lambda values: None)
    # The matching gene still uses the pinned paper-style fresh disable draw.
    monkeypatch.setattr("neat.genes.random", lambda: .99)
    child = CanonicalGenome(100)
    child.configure_crossover(first, second, config)
    assert set(child.connections) == set(first.connections) | set(second.connections)
    assert {gene.innovation for gene in child.connections.values()} == {1, 2, 3, 4, 5}
    assert set(child.nodes) == {0, 10, 11}
    assert child.connections[(-1, 0)].enabled  # disabled parents can re-enable
    for edge in child.connections:
        assert all(node in child.nodes or node in config.input_keys for node in edge)

    # Changing the independent unmatched draws can exclude genes from BOTH parents.
    monkeypatch.setattr("neuroevolution_lab.structural.random.random", lambda: .75)
    child = CanonicalGenome(101); child.configure_crossover(first, second, config)
    assert set(child.connections) == {(-1, 0)}
    assert set(child.nodes) == {0}


def test_tied_parent_genes_have_independent_half_inheritance_and_cycle_guard():
    import neat
    engine = StructuralEngine({"method": "neat", "population_size": 3, "generations": 1})
    config = engine.config.genome_config
    first = _fixture_genome(engine, 1, [(-1, 0, 1, 1., True), (-1, 10, 2, 2., True)])
    second = _fixture_genome(engine, 2, [(-1, 0, 1, 4., True), (-2, 11, 3, 5., True)])
    ambient = random.getstate()
    try:
        inherited = []
        for seed in range(200):
            random.seed(seed)
            child = CanonicalGenome(100+seed); child.configure_crossover(first, second, config)
            inherited.append(((-1, 10) in child.connections, (-2, 11) in child.connections))
        assert set(inherited) == {(False, False), (True, False), (False, True), (True, True)}
        assert all(70 <= sum(row[index] for row in inherited) <= 130 for index in (0, 1))

        # Two acyclic parents whose union contains the 10<->11 cycle.
        first = _fixture_genome(engine, 1, [(-1, 10, 1, 1., True), (10, 11, 2, 1., True), (11, 0, 3, 1., True)])
        second = _fixture_genome(engine, 2, [(-2, 11, 4, 1., True), (11, 10, 5, 1., True), (10, 0, 6, 1., True)])
        for seed in range(100):
            random.seed(seed)
            child = CanonicalGenome(seed+1000); child.configure_crossover(first, second, config)
            assert not ((10, 11) in child.connections and (11, 10) in child.connections)
            assert all(node in child.nodes or node in config.input_keys for edge in child.connections for node in edge)
            assert np.isfinite(neat.nn.FeedForwardNetwork.create(child, engine.config).activate([0., 1.])).all()
    finally:
        random.setstate(ambient)


def test_unequal_fitness_crossover_remains_identical_to_pinned_upstream():
    import neat
    from neuroevolution_lab.structural import serialize_neat
    engine = StructuralEngine({"method": "neat", "population_size": 3, "generations": 1})
    first = _fixture_genome(engine, 1, [(-1, 0, 1, 1., False), (-1, 10, 2, 2., True)], fitness=2.)
    second = _fixture_genome(engine, 2, [(-1, 0, 1, 4., True), (-2, 11, 3, 5., True)], fitness=1.)
    ambient = random.getstate()
    try:
        for criterion in ("max", "min"):
            random.seed(17)
            actual = CanonicalGenome(100); actual.configure_crossover(first, second, engine.config.genome_config, criterion)
            actual_random = random.getstate()
            random.seed(17)
            expected = neat.DefaultGenome(100); expected.configure_crossover(first, second, engine.config.genome_config, criterion)
            assert serialize_neat(actual) == serialize_neat(expected)
            assert random.getstate() == actual_random
    finally:
        random.setstate(ambient)


def test_paper_disabled_inheritance_is_fresh_75_percent_draw(monkeypatch):
    from neat.genes import DefaultConnectionGene
    first = DefaultConnectionGene((-1, 0), innovation=3)
    second = DefaultConnectionGene((-1, 0), innovation=3)
    first.weight = 1.; second.weight = 2.; first.enabled = False; second.enabled = False
    enabled = []
    for draw in np.arange(100)/100:
        draws = iter([.1, .1, float(draw)])  # weight, inherited enabled, fresh disable draw
        monkeypatch.setattr("neat.genes.random", lambda: next(draws))
        enabled.append(first.crossover(second, disable_rule="neat-python").enabled)
    assert sum(enabled) == 25
    monkeypatch.setattr("neat.genes.random", lambda: .99)
    assert first.crossover(second, disable_rule="neat-python").enabled
    assert not first.crossover(second, disable_rule="stanley").enabled


def test_interspecies_repair_and_differential_upstream_equivalence():
    import neat
    from neuroevolution_lab.structural import serialize_neat
    ambient = random.getstate()
    try:
        # With interspecies mating disabled, the narrow adapter is bit-identical.
        engine, _ = _two_species_engine(interspecies=0.)
        reference = copy.deepcopy(engine)
        random.setstate(engine.random_state)
        actual = engine.population.reproduction.reproduce(engine.config, engine.population.species, 12, 0)
        actual_random = random.getstate()
        random.setstate(reference.random_state)
        expected = neat.DefaultReproduction.reproduce(reference.population.reproduction, reference.config,
                                                     reference.population.species, 12, 0)
        assert {k: serialize_neat(v) for k, v in actual.items()} == {k: serialize_neat(v) for k, v in expected.items()}
        assert actual_random == random.getstate()
        # The exact pinned upstream fails when earlier parent species are cleared.
        broken, _ = _two_species_engine(interspecies=1.)
        random.setstate(broken.random_state)
        with pytest.raises(IndexError, match="empty sequence"):
            neat.DefaultReproduction.reproduce(broken.population.reproduction, broken.config, broken.population.species, 12, 0)
        repaired, membership = _two_species_engine(interspecies=1.)
        random.setstate(repaired.random_state)
        children = repaired.population.reproduction.reproduce(repaired.config, repaired.population.species, 12, 0)
        assert len(children) == 12
        assert any(membership[parents[0]] != membership[parents[1]] for key, parents in repaired.population.reproduction.ancestors.items()
                   if key in children and key not in membership)
        assert all(type(s).__name__ == "Species" for s in repaired.population.species.species.values())
    finally:
        random.setstate(ambient)


def test_nas_trains_real_weights_with_separate_validation(monkeypatch):
    architecture = {"widths": [8], "activations": ["tanh"]}
    result = train_architecture(architecture, 5, steps=40)
    assert result["metrics"]["final_training_loss"] < result["metrics"]["initial_training_loss"]
    assert result["metrics"]["trained_state"]
    assert result["metrics"]["parameters"] == architecture_parameters(architecture)
    assert result == train_architecture(architecture, 5, steps=40)
    engine = ModularNASEngine({"method": "modular_nas", "population_size": 3, "generations": 2,
                              "learning": {"steps": 5}, "seed": 1})
    context = Context(); engine.step(context)
    resumed = pickle.loads(pickle.dumps(engine)); engine.step(context); resumed.step(Context())
    assert engine.summary() == resumed.summary()
    assert len(context.evaluations) == 6
    def forbid_training(*args, **kwargs):
        raise AssertionError("Replay must not train")
    monkeypatch.setattr("neuroevolution_lab.structural.train_architecture", forbid_training)
    assert engine.replay() == engine.best_result
    assert engine.replay(seed=10000)["metrics"]["trained_state"] == engine.best_result["metrics"]["trained_state"]


def test_render_saved_genome_and_generated_substrate(tmp_path):
    from neuroevolution_lab.structural import render_genome
    engine = StructuralEngine({"method": "hyperneat", "seed": 1, "population_size": 3, "generations": 1})
    engine.step(Context())
    output = tmp_path / "actual-genome.svg"
    render_genome(engine.summary(), output)
    svg = output.read_text()
    assert "Evolved CPPN" in svg and "Actual expressed substrate weights" in svg
