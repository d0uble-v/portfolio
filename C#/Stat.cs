using System;
using System.Collections.Generic;
using System.Collections.ObjectModel;


namespace Sourcery.Stats
{
    [Serializable]
    public abstract class Stat
    {
        public readonly string name;

        public readonly StatSystem statSystem;


        // Constructor
        public Stat(string name, StatSystem statSystem)
        {
            this.name = name;
            this.statSystem = statSystem;
        }
    }
}