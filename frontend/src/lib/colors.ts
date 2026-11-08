/**
 * Paleta da grade: uma cor por cadeira (não por turma), usada tanto no chip de
 * seleção quanto no bloco da grade. Os tons vêm do protótipo em
 * `static/exampleapp.html`.
 */

export interface GradeColor {
	/** Identificador estável, útil como chave/classe na UI. */
	id: string;
	/** Fundo do bloco. */
	bg: string;
	/** Borda e bolinha do chip. */
	border: string;
	/** Texto sobre o fundo. */
	text: string;
}

export const COLORS: readonly GradeColor[] = [
	{ id: 'roxo', bg: '#EEEDFE', border: '#534AB7', text: '#26215C' },
	{ id: 'verde-agua', bg: '#E1F5EE', border: '#0F6E56', text: '#04342C' },
	{ id: 'coral', bg: '#FAECE7', border: '#993C1D', text: '#4A1B0C' },
	{ id: 'rosa', bg: '#FBEAF0', border: '#993556', text: '#4B1528' },
	{ id: 'azul', bg: '#E6F1FB', border: '#185FA5', text: '#042C53' },
	{ id: 'ambar', bg: '#FAEEDA', border: '#854F0B', text: '#412402' },
	{ id: 'verde', bg: '#EAF3DE', border: '#3B6D11', text: '#173404' }
];

/**
 * Borda dos blocos em conflito. Fica fora da paleta de propósito: é um alerta,
 * não a identidade de uma cadeira.
 */
export const CONFLICT_BORDER = '#CE1126';

/**
 * O mesmo alerta sobre superfície escura. O tom de `CONFLICT_BORDER` foi
 * escolhido para o fundo branco da grade e some no tema escuro dos chips.
 */
export const CONFLICT_BORDER_DARK = '#F87171';

/**
 * Próxima cor a atribuir, dadas as que já estão em uso: a primeira livre na
 * ordem da paleta e, quando todas estão ocupadas, a menos repetida. Remover uma
 * cadeira libera a cor dela para a próxima.
 */
export function nextColor(emUso: readonly GradeColor[]): GradeColor {
	const usos = new Map(COLORS.map((cor) => [cor.id, 0]));
	for (const cor of emUso) {
		usos.set(cor.id, (usos.get(cor.id) ?? 0) + 1);
	}

	let escolhida = COLORS[0];
	for (const cor of COLORS) {
		if (usos.get(cor.id)! < usos.get(escolhida.id)!) escolhida = cor;
	}
	return escolhida;
}
