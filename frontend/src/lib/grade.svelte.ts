import { nextColor, type GradeColor } from './colors';
import { findConflicts, turmasConflict, type Conflict } from './conflicts';
import type { Course, Selection, Turma } from './types';

/**
 * Estado da grade em montagem: quais cadeiras o usuário escolheu e, em cada
 * uma, qual turma está ativa. Uma cadeira entra no máximo uma vez, identificada
 * pelo `code`.
 *
 * A classe só guarda estado e delega a regra de negócio para `conflicts.ts` e
 * `colors.ts` — os componentes chamam estes métodos e leem os `$derived`.
 */

/** Uma cadeira da grade, já resolvida na turma ativa. */
export interface GradeItem {
	course: Course;
	turma: Turma;
	color: GradeColor;
}

/** O que de fato é guardado: a turma é referenciada pela letra. */
interface Escolha {
	course: Course;
	letter: string;
	color: GradeColor;
}

export class Grade {
	#escolhas = $state<Escolha[]>([]);

	/**
	 * Cadeiras da grade, na ordem em que foram adicionadas. Escolhas cuja letra
	 * não existe mais na cadeira (catálogo recarregado) são simplesmente omitidas.
	 */
	readonly items: GradeItem[] = $derived(
		this.#escolhas
			.map(({ course, letter, color }) => {
				const turma = course.turmas.find((t) => t.letter === letter);
				return turma ? { course, turma, color } : null;
			})
			.filter((item): item is GradeItem => item !== null)
	);

	/** As turmas ativas, no formato que `conflicts.ts` consome. */
	readonly selections: Selection[] = $derived(
		this.items.map(({ course, turma }) => ({ course, turma }))
	);

	readonly conflicts: Conflict[] = $derived(findConflicts(this.selections));

	readonly hasConflict: boolean = $derived(this.conflicts.length > 0);

	/** Códigos das cadeiras envolvidas em algum conflito — para destacar na UI. */
	readonly conflictingCodes: string[] = $derived(
		this.conflicts
			.flatMap((c) => [c.a.course.code, c.b.course.code])
			.filter((code, i, todos) => todos.indexOf(code) === i)
	);

	/** Soma dos créditos das cadeiras da grade; créditos não numéricos contam 0. */
	readonly credits: number = $derived(
		this.items.reduce((total, { course }) => total + (Number(course.credits) || 0), 0)
	);

	/**
	 * Adiciona a cadeira à grade. Sem `letter`, escolhe a primeira turma que não
	 * conflita com o que já está na grade (a primeira turma, se todas conflitam).
	 * Devolve `false` — sem alterar nada — se a cadeira já está na grade, não tem
	 * turmas, ou se a letra pedida não existe.
	 */
	adicionarCadeira(course: Course, letter?: string): boolean {
		if (this.contem(course.code)) return false;

		const turma = letter
			? course.turmas.find((t) => t.letter === letter)
			: this.#turmaPadrao(course);
		if (!turma) return false;

		this.#escolhas.push({
			course,
			letter: turma.letter,
			color: nextColor(this.#escolhas.map((e) => e.color))
		});
		return true;
	}

	/** Adiciona várias cadeiras; devolve quantas entraram de fato. */
	adicionarCadeiras(courses: Course[]): number {
		return courses.filter((course) => this.adicionarCadeira(course)).length;
	}

	/** Tira a cadeira da grade. Devolve `false` se ela não estava lá. */
	removerCadeira(code: string): boolean {
		const i = this.#escolhas.findIndex((e) => e.course.code === code);
		if (i === -1) return false;

		this.#escolhas.splice(i, 1);
		return true;
	}

	/** Tira várias cadeiras de uma vez; devolve quantas saíram. */
	removerCadeiras(codes: string[]): number {
		const antes = this.#escolhas.length;

		this.#escolhas = this.#escolhas.filter((e) => !codes.includes(e.course.code));
		return antes - this.#escolhas.length;
	}

	/** Adiciona se não estiver na grade, remove se estiver. Devolve o estado final. */
	alternarCadeira(course: Course): boolean {
		if (this.removerCadeira(course.code)) return false;
		return this.adicionarCadeira(course);
	}

	/**
	 * Troca a turma ativa de uma cadeira já na grade (o clique no chip).
	 * Devolve `false` se a cadeira não está na grade ou a letra não existe.
	 */
	escolherTurma(code: string, letter: string): boolean {
		const escolha = this.#escolhas.find((e) => e.course.code === code);
		if (!escolha) return false;
		if (!escolha.course.turmas.some((t) => t.letter === letter)) return false;

		escolha.letter = letter;
		return true;
	}

	/** Esvazia a grade. */
	limpar(): void {
		this.#escolhas = [];
	}

	contem(code: string): boolean {
		return this.#escolhas.some((e) => e.course.code === code);
	}

	itemDe(code: string): GradeItem | undefined {
		return this.items.find((item) => item.course.code === code);
	}

	/** Turma ativa de uma cadeira da grade. */
	turmaDe(code: string): Turma | undefined {
		return this.itemDe(code)?.turma;
	}

	/** Cor da cadeira — a mesma no chip e no bloco da grade. */
	corDe(code: string): GradeColor | undefined {
		return this.#escolhas.find((e) => e.course.code === code)?.color;
	}

	/** A cadeira está envolvida em algum conflito? */
	emConflito(code: string): boolean {
		return this.conflictingCodes.includes(code);
	}

	/**
	 * Trocar para esta turma criaria conflito? Serve para a UI marcar os chips
	 * problemáticos antes do clique. A própria turma ativa da cadeira é ignorada
	 * na comparação.
	 */
	turmaConflita(code: string, letter: string): boolean {
		const course = this.#escolhas.find((e) => e.course.code === code)?.course;
		const turma = course?.turmas.find((t) => t.letter === letter);
		if (!turma) return false;

		return this.#conflitaComGrade(turma, code);
	}

	/** Primeira turma sem conflito com a grade atual; se todas conflitam, a primeira. */
	#turmaPadrao(course: Course): Turma | undefined {
		return (
			course.turmas.find((turma) => !this.#conflitaComGrade(turma, course.code)) ?? course.turmas[0]
		);
	}

	/** A turma bate com alguma outra cadeira da grade (ignorando `code`)? */
	#conflitaComGrade(turma: Turma, code: string): boolean {
		return this.items.some(
			(item) => item.course.code !== code && turmasConflict(turma, item.turma)
		);
	}
}
