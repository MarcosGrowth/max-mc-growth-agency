import { Composition } from "remotion";
import { MaxAIChat, maxAIChatSchema } from "./components/MaxAIChat";
import { Embudo, embudoSchema } from "./components/Embudo";
import maxai from "./data/maxai.json";
import embudo from "./data/embudo.json";

// Piezas de datos para el reel de MC Growth. Se renderizan con fondo transparente
// y se insertan en la composición de Hyperframes. Para otro reel, cambiá los JSON de src/data.
export const RemotionRoot: React.FC = () => {
  return (
    <>
      <Composition id="MaxAIChat" component={MaxAIChat} schema={maxAIChatSchema} defaultProps={maxai as never}
        durationInFrames={96} fps={30} width={1080} height={1920} />
      <Composition id="Embudo" component={Embudo} schema={embudoSchema} defaultProps={embudo as never}
        durationInFrames={84} fps={30} width={1080} height={1920} />
    </>
  );
};
