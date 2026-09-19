import { PlayerStats } from '../types';
import { calculatePoints } from '../utils/statistics';

export function calculateWinningScore(players: PlayerStats[]): number {
    let totalScore = 0;

    players.forEach(player => {
        totalScore += calculatePoints(player);
    });

    return totalScore;
}

export function getPlayerScore(player: PlayerStats): number {
    return calculatePoints(player);
}