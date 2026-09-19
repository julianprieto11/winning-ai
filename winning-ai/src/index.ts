import { getPlayers } from './data/players';
import { getMatches } from './data/matches';
import { calculateWinningScore } from './scoring/winning-score';
import { calculateSafeTeam } from './predictions/safe-team';
import { calculateRiskyTeam } from './predictions/risky-team';
import { calculateBalancedTeam } from './predictions/balanced-team';
import { validateLineup } from './predictions/lineup-validator';

async function main() {
    const players = await getPlayers();
    const matches = await getMatches();

    const safeTeam = calculateSafeTeam(players, matches);
    const riskyTeam = calculateRiskyTeam(players, matches);
    const balancedTeam = calculateBalancedTeam(players, matches);

    const isValidSafeTeam = validateLineup(safeTeam);
    const isValidRiskyTeam = validateLineup(riskyTeam);
    const isValidBalancedTeam = validateLineup(balancedTeam);

    console.log('Safe Team:', safeTeam, 'Valid:', isValidSafeTeam);
    console.log('Risky Team:', riskyTeam, 'Valid:', isValidRiskyTeam);
    console.log('Balanced Team:', balancedTeam, 'Valid:', isValidBalancedTeam);
}

main().catch(error => {
    console.error('Error executing the program:', error);
});