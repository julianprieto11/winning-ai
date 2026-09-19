import { Player } from '../types';
import { validateFormation } from '../utils/statistics';

const REQUIRED_PLAYERS = {
    goalkeeper: 1,
    defenders: 3,
    midfielders: 3,
    forwards: 3,
};

const FLEX_OPTIONS = {
    defender: 1,
    midfielder: 1,
    forward: 1,
};

export function validateLineup(lineup: Player[], flexOptions: Player[]): boolean {
    const formationValid = validateFormation(lineup, REQUIRED_PLAYERS);
    const flexValid = validateFlexOptions(flexOptions);

    return formationValid && flexValid;
}

function validateFlexOptions(flexOptions: Player[]): boolean {
    const flexCounts = {
        defender: 0,
        midfielder: 0,
        forward: 0,
    };

    for (const player of flexOptions) {
        if (player.position === 'defender') {
            flexCounts.defender++;
        } else if (player.position === 'midfielder') {
            flexCounts.midfielder++;
        } else if (player.position === 'forward') {
            flexCounts.forward++;
        }
    }

    return (
        flexCounts.defender <= FLEX_OPTIONS.defender &&
        flexCounts.midfielder <= FLEX_OPTIONS.midfielder &&
        flexCounts.forward <= FLEX_OPTIONS.forward
    );
}