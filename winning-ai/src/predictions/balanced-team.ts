import { Player, Team } from '../types';
import { getPlayers } from '../data/players';
import { calculateWinningScore } from '../scoring/winning-score';

export function calculateBalancedTeam(): { team: Team; flexOptions: Player[] } {
    const players = getPlayers();
    
    // Sort players based on their scores
    const sortedPlayers = players.sort((a, b) => calculateWinningScore(b) - calculateWinningScore(a));

    // Select players for the balanced team
    const team: Team = {
        goalkeeper: sortedPlayers.find(player => player.position === 'GK') || null,
        defenders: sortedPlayers.filter(player => player.position === 'DEF').slice(0, 3),
        midfielders: sortedPlayers.filter(player => player.position === 'MID').slice(0, 3),
        forwards: sortedPlayers.filter(player => player.position === 'FWD').slice(0, 3),
    };

    // Select flex options
    const flexOptions: Player[] = [
        ...sortedPlayers.filter(player => player.position === 'DEF').slice(3, 4),
        ...sortedPlayers.filter(player => player.position === 'MID').slice(3, 4),
        ...sortedPlayers.filter(player => player.position === 'FWD').slice(3, 4),
    ];

    return { team, flexOptions };
}