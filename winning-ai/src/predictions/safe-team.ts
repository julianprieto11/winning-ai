import { Player } from '../types';
import { getPlayers } from '../data/players';
import { calculateWinningScore } from '../scoring/winning-score';

export function calculateSafeTeam(): Player[] {
    const players = getPlayers();
    
    // Ordenar jugadores por puntuación esperada
    const sortedPlayers = players.sort((a, b) => {
        return calculateWinningScore(b) - calculateWinningScore(a);
    });

    const safeTeam: Player[] = [];
    const flexOptions: Player[] = [];

    // Seleccionar 10 jugadores para el equipo seguro
    let goalkeepers = 0;
    let defenders = 0;
    let midfielders = 0;
    let forwards = 0;

    for (const player of sortedPlayers) {
        if (safeTeam.length < 10) {
            if (player.position === 'GK' && goalkeepers < 1) {
                safeTeam.push(player);
                goalkeepers++;
            } else if (player.position === 'DEF' && defenders < 3) {
                safeTeam.push(player);
                defenders++;
            } else if (player.position === 'MID' && midfielders < 3) {
                safeTeam.push(player);
                midfielders++;
            } else if (player.position === 'FWD' && forwards < 3) {
                safeTeam.push(player);
                forwards++;
            }
        }
    }

    // Seleccionar opciones para el flex
    for (const player of sortedPlayers) {
        if (flexOptions.length < 3 && !safeTeam.includes(player)) {
            if (player.position === 'DEF' && flexOptions.filter(p => p.position === 'DEF').length < 1) {
                flexOptions.push(player);
            } else if (player.position === 'MID' && flexOptions.filter(p => p.position === 'MID').length < 1) {
                flexOptions.push(player);
            } else if (player.position === 'FWD' && flexOptions.filter(p => p.position === 'FWD').length < 1) {
                flexOptions.push(player);
            }
        }
    }

    return [...safeTeam, ...flexOptions];
}