import { Player } from '../types';
import { calculatePotentialPoints } from '../utils/statistics';
import { players } from '../data/players';

export function getRiskyTeam(): { team: Player[]; flexOptions: Player[] } {
    const sortedPlayers = players.sort((a, b) => {
        const potentialA = calculatePotentialPoints(a);
        const potentialB = calculatePotentialPoints(b);
        return potentialB - potentialA; // Sort by potential points in descending order
    });

    const riskyTeam: Player[] = [];
    const flexOptions: Player[] = [];

    let goalkeepers = 0;
    let defenders = 0;
    let midfielders = 0;
    let forwards = 0;

    for (const player of sortedPlayers) {
        if (riskyTeam.length >= 10 && flexOptions.length >= 3) break;

        if (player.position === 'GK' && goalkeepers < 1) {
            riskyTeam.push(player);
            goalkeepers++;
        } else if (player.position === 'DEF' && defenders < 3) {
            riskyTeam.push(player);
            defenders++;
        } else if (player.position === 'MID' && midfielders < 3) {
            riskyTeam.push(player);
            midfielders++;
        } else if (player.position === 'FWD' && forwards < 3) {
            riskyTeam.push(player);
            forwards++;
        } else if (flexOptions.length < 3) {
            if (player.position === 'DEF' && defenders < 4) {
                flexOptions.push(player);
            } else if (player.position === 'MID' && midfielders < 4) {
                flexOptions.push(player);
            } else if (player.position === 'FWD' && forwards < 4) {
                flexOptions.push(player);
            }
        }
    }

    return { team: riskyTeam, flexOptions };
}