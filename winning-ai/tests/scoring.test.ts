import { calculateWinningScore } from '../src/scoring/winning-score';
import { Player } from '../src/types';
import { getPlayers } from '../src/data/players';

describe('Scoring System Tests', () => {
    let players: Player[];

    beforeAll(() => {
        players = getPlayers();
    });

    test('should calculate correct score for a player', () => {
        const player = players[0]; // Assuming the first player is valid
        const score = calculateWinningScore(player);
        expect(score).toBeGreaterThanOrEqual(0); // Score should not be negative
    });

    test('should handle players with no stats', () => {
        const player = { ...players[0], goals: 0, assists: 0 }; // Mock player with no stats
        const score = calculateWinningScore(player);
        expect(score).toBe(0); // Score should be zero for no contributions
    });

    test('should calculate scores for all players', () => {
        players.forEach(player => {
            const score = calculateWinningScore(player);
            expect(score).toBeDefined(); // Each player should have a defined score
        });
    });
});