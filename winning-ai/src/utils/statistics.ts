import { PlayerStats } from '../types';

export function calculateAverageStats(players: PlayerStats[], statKey: keyof PlayerStats): number {
    const total = players.reduce((sum, player) => sum + player[statKey], 0);
    return total / players.length;
}

export function calculateMaxStat(players: PlayerStats[], statKey: keyof PlayerStats): PlayerStats | null {
    return players.reduce((maxPlayer, player) => {
        return maxPlayer === null || player[statKey] > maxPlayer[statKey] ? player : maxPlayer;
    }, null as PlayerStats | null);
}

export function calculateMinStat(players: PlayerStats[], statKey: keyof PlayerStats): PlayerStats | null {
    return players.reduce((minPlayer, player) => {
        return minPlayer === null || player[statKey] < minPlayer[statKey] ? player : minPlayer;
    }, null as PlayerStats | null);
}

export function calculatePlayerConsistency(players: PlayerStats[], statKey: keyof PlayerStats): number {
    const average = calculateAverageStats(players, statKey);
    const variance = players.reduce((sum, player) => sum + Math.pow(player[statKey] - average, 2), 0) / players.length;
    return Math.sqrt(variance);
}