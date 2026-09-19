import { calculateSafeTeam } from '../src/predictions/safe-team';
import { calculateRiskyTeam } from '../src/predictions/risky-team';
import { calculateBalancedTeam } from '../src/predictions/balanced-team';

describe('Predictions Tests', () => {
    test('should calculate the safest team correctly', () => {
        const safeTeam = calculateSafeTeam();
        expect(safeTeam).toHaveLength(10);
        expect(safeTeam).toEqual(
            expect.arrayContaining([
                expect.objectContaining({ position: 'arq' }),
                expect.objectContaining({ position: 'def' }),
                expect.objectContaining({ position: 'vol' }),
                expect.objectContaining({ position: 'del' }),
            ])
        );
    });

    test('should calculate the riskiest team correctly', () => {
        const riskyTeam = calculateRiskyTeam();
        expect(riskyTeam).toHaveLength(10);
        expect(riskyTeam).toEqual(
            expect.arrayContaining([
                expect.objectContaining({ position: 'arq' }),
                expect.objectContaining({ position: 'def' }),
                expect.objectContaining({ position: 'vol' }),
                expect.objectContaining({ position: 'del' }),
            ])
        );
    });

    test('should calculate the balanced team correctly', () => {
        const balancedTeam = calculateBalancedTeam();
        expect(balancedTeam).toHaveLength(10);
        expect(balancedTeam).toEqual(
            expect.arrayContaining([
                expect.objectContaining({ position: 'arq' }),
                expect.objectContaining({ position: 'def' }),
                expect.objectContaining({ position: 'vol' }),
                expect.objectContaining({ position: 'del' }),
            ])
        );
    });
});