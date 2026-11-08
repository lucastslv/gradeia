import type { Selection, Session, Turma } from './types';

/** Duas seleções cujos horários se sobrepõem, com as sessões culpadas. */
export interface Conflict {
	a: Selection;
	b: Selection;
	/** As sessões que efetivamente se sobrepõem (mesmo dia, intervalos cruzados). */
	sessions: [Session, Session];
}

/**
 * Duas sessões conflitam quando caem no mesmo dia e seus intervalos se cruzam.
 * Intervalos são semi-abertos: uma aula que termina 10:30 não conflita com uma
 * que começa 10:30.
 */
export function sessionsOverlap(a: Session, b: Session): boolean {
	return a.day === b.day && a.start < b.end && b.start < a.end;
}

/** Verdadeiro se qualquer sessão de `a` se sobrepõe a qualquer sessão de `b`. */
export function turmasConflict(a: Turma, b: Turma): boolean {
	return a.sessions.some((sa) => b.sessions.some((sb) => sessionsOverlap(sa, sb)));
}

/**
 * Todos os pares de seleções em conflito, comparando cada par uma única vez.
 * Sessões da mesma turma nunca são comparadas entre si.
 */
export function findConflicts(selections: Selection[]): Conflict[] {
	const conflicts: Conflict[] = [];

	for (let i = 0; i < selections.length; i++) {
		for (let j = i + 1; j < selections.length; j++) {
			const a = selections[i];
			const b = selections[j];

			for (const sa of a.turma.sessions) {
				for (const sb of b.turma.sessions) {
					if (sessionsOverlap(sa, sb)) {
						conflicts.push({ a, b, sessions: [sa, sb] });
					}
				}
			}
		}
	}

	return conflicts;
}

/** Atalho para a UI: a grade tem algum conflito? */
export function hasConflict(selections: Selection[]): boolean {
	return findConflicts(selections).length > 0;
}
