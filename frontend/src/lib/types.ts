/** Uma sessão é um encontro semanal: um dia e um intervalo de horário. */
export interface Session {
	/** 0=Segunda, 1=Terça, 2=Quarta, 3=Quinta, 4=Sexta, 5=Sábado */
	day: number;
	/** Minutos desde meia-noite (ex: 8:30 = 510) */
	start: number;
	/** Minutos desde meia-noite */
	end: number;
}

export interface Turma {
	/** ex: "A", "B2", "U" */
	letter: string;
	/** Uma turma pode ter múltiplas sessões (dias) */
	sessions: Session[];
	campus: string | null;
	local: string | null;
}

export interface Course {
	/** ex: "INF01203" */
	code: string;
	name: string;
	credits: number;
	/** "ofertada" | "nao_ofertada" | "nao_publicado" */
	estado: string;
	carater: string;
	etapa: number | null;
	turmas: Turma[];
}

/** Uma turma escolhida pelo usuário, junto da matéria a que pertence. */
export interface Selection {
	course: Course;
	turma: Turma;
}

export const DAY_NAMES = ['Segunda', 'Terça', 'Quarta', 'Quinta', 'Sexta', 'Sábado'] as const;

/** Os mesmos dias abreviados, para o cabeçalho da grade. */
export const DAY_ABBR = ['Seg', 'Ter', 'Qua', 'Qui', 'Sex', 'Sáb'] as const;
